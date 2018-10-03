#!/bin/bash

repoUrl='http://ci-nexus.englab.juniper.net/repository/vmware-releases/'
VERSION='7.3.0'

# Deploy artifacts composed of a pom, jar, sources and javadocs jar

cd 4
for file in `ls -A1 | grep pom`; do prefix=${file%%-${VERSION}*}; mvn deploy:deploy-file -DpomFile=${prefix}-${VERSION}.pom \
  -Dfile=${prefix}-${VERSION}.jar -Djavadoc=${prefix}-${VERSION}-javadoc.jar -Dsources=${prefix}-${VERSION}-sources.jar \
  -DrepositoryId=nexus -Durl=$repoUrl; done

cd ..

# Deploy artifacts composed of pom, jar and sources jar

cd 3
for file in `ls -A1 | grep sources`; do prefix=${file%%-${VERSION}*}; mvn deploy:deploy-file -DpomFile=${prefix}-${VERSION}.pom \
  -Dfile=${prefix}-${VERSION}.jar -Dsources=${prefix}-${VERSION}-sources.jar -DrepositoryId=nexus -Durl=$repoUrl; done

# Deploy artifacts composed of pom, jar and javadoc jar

for file in `ls -A1 | grep javadoc`; do prefix=${file%%-${VERSION}*}; mvn deploy:deploy-file -DpomFile=${prefix}-${VERSION}.pom \
  -Dfile=${prefix}-${VERSION}.jar -Djavadoc=${prefix}-${VERSION}-javadoc.jar -DrepositoryId=nexus  -Durl=$repoUrl; done

# Deploy artifacts composed of pom, jar and jar-with-dependencies jar

for file in `ls -A1 | grep jar-with-dep`; do prefix=${file%%-${VERSION}*}; mvn deploy:deploy-file \
  -DpomFile=${prefix}-${VERSION}.pom -Dfile=${prefix}-${VERSION}-jar-with-dependencies.jar -Dclassifier=jar-with-dependencies \
  -DrepositoryId=nexus -Durl=$repoUrl; mvn deploy:deploy-file -DpomFile=${prefix}-${VERSION}.pom -Dfile=${prefix}-${VERSION}.jar \
  -DrepositoryId=nexus -Durl=$repoUrl; done

cd ..

# Deploy artifacts composed of a pom and jar

cd 2
for file in `ls -A1 | grep pom`; do  prefix=${file%%-${VERSION}*}; mvn deploy:deploy-file -DpomFile=${prefix}-${VERSION}.pom \
  -Dfile=${prefix}-${VERSION}.jar -DrepositoryId=nexus -Durl=$repoUrl; done

cd ..

# Deploy artifacts which are only pom files

cd 1
for file in `ls -A1 | grep pom`; do mvn deploy:deploy-file -DpomFile=$file -Dfile=$file -DrepositoryId=nexus -Durl=$repoUrl; done
