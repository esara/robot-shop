#!/bin/sh

source .env

# docker-buildx for multiarch or docker-compose for x86
BUILD_TOOL=${1:-docker-buildx}

if [ "$BUILD_TOOL" == "docker-compose" ]; then
  docker-compose build
  docker compose -f docker-compose.yaml -f docker-compose-load.yaml build load
fi

for DFILE in $(find . -name Dockerfile -print)
do
    IMAGE=$(awk -F "/" '{print $2}' <<< "$DFILE")

    if [[ "$IMAGE" == "mongo" ]]; then
      CONTAINER=rs-${IMAGE}db
    elif [[ "$IMAGE" == "mysql-loader" ]]; then
      CONTAINER=rs-loader
    elif [[ "$IMAGE" == "load-gen" ]]; then
      CONTAINER=rs-load
    elif [[ "$IMAGE" == "fluentd" ]]; then
      continue
    else
      CONTAINER=rs-${IMAGE}
    fi

    if [ "$BUILD_TOOL" == "docker-buildx" ]; then
      echo "Building $CONTAINER"
      docker buildx build --platform linux/amd64,linux/arm64/v8 --push ./${IMAGE} -f ./${IMAGE}/Dockerfile -t ${REPO}/${CONTAINER}
    elif [ "$BUILD_TOOL" == "docker-compose" ]; then
      echo "Pushing $CONTAINER"
      docker push ${REPO}/${CONTAINER}:${TAG}
    else
        echo "Unknown build_tool: $BUILD_TOOL. Supported options are 'docker-buildx' or 'docker-compose'."
        exit 1
    fi
done
