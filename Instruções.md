Baseado em:
    https://github.com/RikKraanVantage/kubernetes-flask-mysql
    https://www.kdnuggets.com/2021/02/deploy-flask-api-kubernetes-connect-micro-services.html

1. O banco de dados precisa basicamente de duas coisas. 1) Credenciais configuradas para acesso e 2) um volume persistente para manter seus dados;

    1.1 - Gerando o arquivo secrets.yaml
    As credenciais serão fornecidadas através de um 'secret', que é a forma que o Kubernetes armazena de forma segura credenciais, e essas podem ser consumidas pelos pods como se fosse variáveis ambientes. As credenciais devem ser codificadas como base64. Assim, serão criados duas credencias e então elas serão descritas em um arquivo yaml.

    $ echo -n 'Senha%#123'|base64
    U2VuaGElIzEyMw==
    $ echo -n 'flaskpass'|base64
    Zmxhc2twYXNz

    secrets.yaml

        apiVersion: v1
        kind: Secret
        metadata:
            name: flaskapi-secrets
        type: Opaque
        data:
            db_root_password: U2VuaGElIzEyMw==  # Senha%#123  echo -n 'Senha%#123'|base64
            db_flask_password: Zmxhc2twYXNz     # flaskpass

    O metadata.name deverá ser lembrado para uso posterior.
    O secrets deverá ser disponibilizado no cluster com:
        $ kubectl apply -f secrets.yaml
    
    1.2 - Gerando o volume persistente

    Um persistent volume é um recurso de armazenamento com um cliclo de vida independente de um Pod. Isso sgnifica que se o pod vinher a cair, o volume se matém. Um persistent storage pode ser um diretório em um sistema local, mas também pode ser um um storage service do provedor de nuvem tal como o EBS ou Azure Disk. O tipo de peristent volume pode ser especificado no momento da criaão.
    Para uma aplicação usar um persistent volume são necessários dois passos:
 
        1. Especificar o tipo atual de storage, localização, tamanho e propriedades do volume;
        2. Especificar um 'persistent volume claim' que requisita um tamanho específico e modo de acesso do 'persistent volume' para o deployment

    Criar o arquivo persistent-volume.yaml e especiicar o tamanho (2GB), modo de acesso e caminho onde os arquivos serão armazenados.
    O spec.persistentVolumeReclaimPolicy especifica o que deverá ser feito caso o 'persisten volume claim' seja deletado. No caso de uma aplicação 'stateful' como MySQL vamos querer manter os dados se o claim for deletado, assim podemos manualmente obter ou fazer backup dos dados. O default reclaim policy é herdado do tipo de persisten volume, assim é uma boa prática sempre especificiar no yml.

        apiVersion: v1
        kind: PersistentVolume
        metadata:
        name: mysql-pv-volume
        labels:
            type: local
        spec:
        storageClassName: manual
        capacity:
            storage: 2Gi
        accessModes:
            - ReadWriteOnce
        persistentVolumeReclaimPolicy: Retain
        hostPath:
            path: "/mnt/data"
        ---
        apiVersion: v1
        kind: PersistentVolumeClaim
        metadata:
        name: mysql-pv-claim
        spec:
        storageClassName: manual
        accessModes:
            - ReadWriteOnce
        resources:
            requests:
            storage: 2Gi
    
   A adição do strage deve ser feita através do comando 'kubectl apply -f persisten-volume.yaml'. E os detalhes podem ser verificados através dos comandos 'kubectl describe pv mysql-pv-volume' e kubectl describe pvc mysql-pv-claim.
   Como foi feito um volume do tipo 'hostPath', os dados podem ser acessados no node e encontados em /mnt/data;

2. Fazendo o Deploy do MySQL

    Com os segredos e persistent volume no lugar, podemos iniciar a construção da nossa aplicação. Primeiro iremos fazer o deploy do MySQL server. Fazer o pull da mais nova imagem do mysql (docker pull mysql) e criar o arquivo mysql-deployment.yaml. Algumas coisas devem ser especificadas.
        1. Haverá apenas uma réplica do pod; (spec.replicas: 1)
        2. O deploymente irá gerenciar todos os pods com a label 'db' (spec.selector.matchLabels.app: db)
        3. O campo template e todos os sub-campos especificarão características do pod. Ele irá executar uma imagem mysql, com o nome mysql e obterá o campo db_root_password através do segredo criado anteriormente em flaskapi-secrets e irá através dessa informação configurar a variável ambiente MYSQL_ROOT_PASSWORD. Além disso será especificada a porta que será exposta do pod bem como o caminho onde deverá ser montado o volume persistente (spec.selector.template.spec.containers.volumeMounts.mountPath: /var/lib/mysql).
        Em seguida será especificado um serviço chamado mysql do tipo LoadBalancer que será usado para acessarmos o banco através desse serviço.

            ---
            apiVersion: apps/v1
            kind: Deployment
            metadata:
            name: mysql
            labels:
                app: db
            spec:
            replicas: 1
            selector:
                matchLabels:
                app: db
            template:
                metadata:
                labels:
                    app: db
                spec:
                containers:
                - name: mysql
                    image: mysql
                    imagePullPolicy: Never
                    env:
                    - name: MYSQL_ROOT_PASSWORD
                    valueFrom:
                        secretKeyRef:
                        name: flaskapi-secrets
                        key: db_root_password
                    ports:
                    - containerPort: 3306
                    name: db-container
                    volumeMounts:
                    - name: mysql-persistent-storage
                        mountPath: /var/lib/mysql
                volumes:
                    - name: mysql-persistent-storage
                    persistentVolumeClaim:
                        claimName: mysql-pv-claim


            ---
            apiVersion: v1
            kind: Service
            metadata:
            name: mysql
            labels:
                app: db
            spec:
            ports:
            - port: 3306
                protocol: TCP
                name: mysql
            selector:
                app: db
            type: LoadBalancer  
        
    Com o arquivo gerado, deve-se aplicá-lo através do comando 'kubectl apply -f mysql-deployment.yaml'

3. Criando o banco de dados e tabelas

    A última coisa  a fazer antes de implementar a API é incializar um banco de dados e um esquema no MySQL server. Por motivos de simplicidade, acessaremos o MySQL através do recém criado serviço. Como o pod executando oserviço está apenas disponível de dentro do cluster, nós iniciaremos um pod temporário que servirá como um mysql-client.

    3.1 Configurar o mysql-client via terminal: kubectl run -it --rm --image=mysql --restart=Never mysql-client -- mysql --host mysql --password=<senha no formato original>
        $ kubectl run -it --rm --image=mysql --restart=Never mysql-client -- mysql --host mysql --password="Senha%#123"

        Obs.: Pode ser necessário criar as regras de firewall para o pod receber acesso na porta 3306
    
    3.2 O seguinte arquivo de schema deverá ser executado na console do MySQL

        CREATE DATABASE flaskdocker;
        USE flaskdocker;
        CREATE TABLE `flaskdocker`.`users` (
            `id` INT NOT NULL AUTO_INCREMENT,
            `name` VARCHAR(255),
            PRIMARY KEY (ID));

        CREATE USER 'flaskuser'@'%' IDENTIFIED BY 'flaskpass';
        GRANT SELECT ON flaskdocker . * TO 'flaskuser'@'%';
        GRANT INSERT ON flaskdocker . * TO 'flaskuser'@'%';
        GRANT UPDATE ON flaskdocker . * TO 'flaskuser'@'%';
        GRANT DELETE ON flaskdocker . * TO 'flaskuser'@'%';

4. Construindoo deploy do Flask no Kubernetes

