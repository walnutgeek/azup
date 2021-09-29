# minikube cheatsheet

## Install stuff

    curl -LO https://storage.googleapis.com/minikube/releases/latest/minikube-darwin-amd64
    sudo install minikube-darwin-amd64 /usr/local/bin/minikube
    minikube version
    minikube start
    kubectl version --short
    curl -LO "https://dl.k8s.io/release/$(curl -L -s https://dl.k8s.io/release/stable.txt)/bin/darwin/amd64/kubectl"
    chmod +x ./kubectl
    mv ./kubectl /usr/local/bin/kubectl
    kubectl version --short

 ## NFS server demo

    docker run -d --rm --privileged --name nfs-server -v /var/nfs:/var/nfs phico/nfs-server:latest
    docker ps
    docker network list
    docker network connect minikube nfs-server
    docker network list
    docker network inspect minikube

    cd k8s/
    git clone https://github.com/phcollignon/nfs-server-minikube.git
    cd nfs-server-minikube/
    kubectl apply -f examples/busybox-nfs.yaml 
    sudo mkdir /var/nfs
    docker run -d --rm --privileged --name nfs-server -v /var/nfs:/var/nfs phico/nfs-server:latest
    kubectl get services
    kubectl get pods --all-namespaces 
    kubectl get pods -o wide 
    kubectl delete -f examples/busybox-nfs.yaml 
    kubectl apply -f examples/busybox-nfs.yaml 
    find /var/nfs/ -ls
    minikube addons enable ingress

    #optional
    cd nfs-subdir-external-provisioner/deploy/
    kubectl apply -f rbac.yaml
    kubectl apply -f deployment.yaml
    kubectl apply -f storageClass.yaml
    cd -
    # optional
    cd csi-driver-nfs/deploy/
    kubectl apply -f rbac-csi-nfs-controller.yaml
    kubectl apply -f csi-nfs-driverinfo.yaml
    kubectl apply -f csi-nfs-controller.yaml
    kubectl apply -f csi-nfs-node.yaml
    cd -

    kubectl delete -f examples/busybox-nfs.yaml 
    kubectl get pods
    kubectl apply -f examples/busybox-nfs.yaml 
    find /var/nfs/ -ls

realized that NFS is not supported in docker host

## configure ingress

    minikube stop
    minikube start
    minikube addons enable ingress
    minikube logs --file=logs.txt

    minikube start --driver='hyperkit' && minikube addons enable ingress
    minikube start --driver=docker
    minikube stop
    minikube delete
    kubectl get pods --all-namespaces
    minikube delete --all --purge
    minikube start --driver='docker' && minikube addons enable ingress

    minikube start --addons=ingress
    kubectl -n ingress-nginx delete pod,svc --all 
    kubectl get pods -A

Things I tried from https://github.com/kubernetes/minikube/issues/10544:

    kubectl delete -A ValidatingWebhookConfiguration ingress-nginx-admission
    docker pull pollyduan/ingress-nginx-controller:v0.44.0
    docker tag pollyduan/ingress-nginx-controller:v0.44.0 k8s.gcr.io/ingress-nginx/controller:v0.44.0
    docker pull k8s.gcr.io/ingress-nginx/kube-webhook-certgen:v1.0
    docker pull k8s.gcr.io/ingress-nginx/controller:v1.0.0-beta.3

Eventially figure out that problem was in PROXY configuration: use FQDN, and exclude right networks in short. See: https://minikube.sigs.k8s.io/docs/handbook/vpn_and_proxy/


## Storage Demo

    git clone https://github.com/phcollignon/kubernetes_storage.git
    cd kubernetes_storage/
    cd lab1_volume_final/yaml/
    for i in backend/*yaml; do kubectl delete -f $i; done
    for i in backend/*yaml; do kubectl apply -f $i; done
