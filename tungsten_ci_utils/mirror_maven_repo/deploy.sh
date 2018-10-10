#!/bin/bash

# Deploys artifacts to a given maven repository assuming the directory structure created by segregate.sh script

usage() {
  echo "Usage: $0 -r <repo url> -v <version>"
  exit 1
}

while getopts "r:v:" opt; do
  case "${opt}" in
    r)
      repoUrl="${OPTARG}"
      ;;
    v)
      VERSION="${OPTARG}"
      ;;
    *)
      usage
      ;;
  esac
done

if [ "x" == "x${repoUrl}" ] || [ "x" == "x${VERSION}" ]; then
  usage
fi

# Deploy artifacts composed of a pom, jar, sources and javadocs jar

cd all
for file in $(ls -A1 | grep pom); do prefix=${file%%-${VERSION}*}; mvn deploy:deploy-file -DpomFile=${prefix}-${VERSION}.pom \
  -Dfile=${prefix}-${VERSION}.jar -Djavadoc=${prefix}-${VERSION}-javadoc.jar -Dsources=${prefix}-${VERSION}-sources.jar \
  -DrepositoryId=nexus -Durl=${repoUrl}; done

cd ..

# Deploy artifacts composed of pom, jar and sources jar
cd sources
for file in $(ls -A1 | grep sources); do prefix=${file%%-${VERSION}*}; mvn deploy:deploy-file -DpomFile=${prefix}-${VERSION}.pom \
  -Dfile=${prefix}-${VERSION}.jar -Dsources=${prefix}-${VERSION}-sources.jar -DrepositoryId=nexus -Durl=${repoUrl}; done

cd ..

# Deploy artifacts composed of pom, jar and javadoc jar
cd javadocs
for file in $(ls -A1 | grep javadoc); do prefix=${file%%-${VERSION}*}; mvn deploy:deploy-file -DpomFile=${prefix}-${VERSION}.pom \
  -Dfile=${prefix}-${VERSION}.jar -Djavadoc=${prefix}-${VERSION}-javadoc.jar -DrepositoryId=nexus  -Durl=${repoUrl}; done

cd ..

# Deploy artifacts composed of pom, jar and jar-with-dependencies jar
cd jars
for file in $(ls -A1 | grep jar-with-dep); do prefix=${file%%-${VERSION}*}; mvn deploy:deploy-file \
  -DpomFile=${prefix}-${VERSION}.pom -Dfile=${prefix}-${VERSION}-jar-with-dependencies.jar -Dclassifier=jar-with-dependencies \
  -DrepositoryId=nexus -Durl=${repoUrl}; mvn deploy:deploy-file -DpomFile=${prefix}-${VERSION}.pom -Dfile=${prefix}-${VERSION}.jar \
  -DrepositoryId=nexus -Durl=${repoUrl}; done

# Deploy artifacts composed of a pom and jar
for file in $(ls -A1 | grep pom); do  prefix=${file%%-${VERSION}*}; mvn deploy:deploy-file -DpomFile=${prefix}-${VERSION}.pom \
  -Dfile=${prefix}-${VERSION}.jar -DrepositoryId=nexus -Durl=${repoUrl}; done

cd ..

# Deploy artifacts which are only pom files

cd poms
for file in $(ls -A1 | grep pom); do mvn deploy:deploy-file -DpomFile=${file} -Dfile=${file} -DrepositoryId=nexus -Durl=${repoUrl}; done
