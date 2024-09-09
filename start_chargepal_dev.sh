#!/usr/bin/env bash

if [ $# -eq 0 ]
then
    echo "Usage:"
    echo
    echo "  `basename $0` (b | build)   [<containers>]      Build or rebuild"
    echo "  `basename $0` (U | update)  [<containers>]      download latest images"
    echo "  `basename $0` (d | down)    [<containers>]      Stop and remove"
    echo "  `basename $0` (r | run)     [<containers>]      Run"
    echo "  `basename $0` (s | stop)    [<containers>]      Stop (halt)"
    echo "  `basename $0` (k | kill)    [<containers>]      Kill"
    echo "  `basename $0` ps            [<containers>]      List"
    echo "  `basename $0` rm            [<containers>]      Remove"
    echo "  `basename $0` stats                             Show statistics"
    echo
    echo "  `basename $0` (l | log)    <container>            Show log tail (last 100 lines)"
    echo "  `basename $0` (e | exec)   <container> <command>  Execute command"
    echo "  `basename $0` (a | attach) <container>            Attach to container with shell"
    echo
    echo "  `basename $0` prune      Remove all unused containers, networks and images"
    echo "  `basename $0` stopall    Stop all running containers (system-wide!)"
    echo "  `basename $0` killall    Kill all running containers (system-wide!)"
    echo
    echo "Arguments:"
    echo
    echo "  containers    One or more containers (omit to affect all containers)"
    echo "  container     Excactly one container to be affected"
    echo "  command       Command to be executed inside a container"
    exit
fi

name="chargepal_local_server_dev"



cmd=$1
cmd_args=${@:2}
echo $cmd_args

run_args="-it --rm" 
run_args+=" -v $(pwd):/root/chargepal_local_server" 
run_args+=" --shm-size=2gb"
run_args+=" -h $HOSTNAME"
run_args+=" --name $name"
run_args+=" --runtime=nvidia"
run_args+=" -e NVIDIA_VISIBLE_DEVICES=all"
run_args+=" -p 50059:50059"
run_args+=" -p 8080:8080"
if [ -f ".env" ]; then
    run_args+=" --env-file=.env"
    source .env
fi

if [ -f ".git_credentials" ]
then
    source .git_credentials
fi

build_args="--build-arg MAKEFLAGS=-j6 --build-arg CI_DEPLOY_USER=$CI_DEPLOY_USER --build-arg CI_DEPLOY_PASSWORD=$CI_DEPLOY_PASSWORD --progress=plain --load "
image="chargepal_local_server_dev"
echo $image
echo $run_args
set -x

case $cmd in
    b | build)
        docker build -f docker/Dockerfile.noetic -t $image $build_args $cmd_args .
        # DOCKER_BUILDKIT=1 docker build . -f $name.dockerfile -t ${image}-dev $build_args $cmd_args
        ;;
    U | update)
	    docker pull ${image}
        docker pull ${image}-dev
	;;
    d | debug)
        docker run $run_args $image-dev /app/start.sh debug
        ;;
    r | run)
        docker run $run_args $image $cmd_args
	;;
    ri | run-image)
    	docker run $run_args $image $cmd_args bash
        ;;
    p | push)
        docker push ${image}-dev 
        docker push $image
        ;;
    s | stop)
        docker stop $name $cmd_args
        ;;
    k | kill)
        docker kill $name $cmd_args
        ;;
    d | rm)
        docker kill $name
        docker rm $name $cmd_args
        ;;
    l | log | logs)
        docker logs -f --tail 100 $cmd_args $name
        ;;
    e | exec)
        docker exec $name $cmd_args 
        ;;
    a | attach)
        docker exec -it $cmd_args $name /bin/bash
        ;;
    *)
        echo "Unsupported command \"$cmd\""
        exit 1
esac
