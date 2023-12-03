#
# Build
#
FROM debian:12 AS build

RUN apt-get update && apt-get -y install maven

WORKDIR /opt/shipping

COPY pom.xml /opt/shipping/
RUN mvn dependency:resolve
COPY src /opt/shipping/src/
RUN mvn package

#
# Run
#
FROM openjdk:25-jdk

EXPOSE 8080

WORKDIR /opt/shipping

ENV CART_ENDPOINT=cart:8080
ENV DB_HOST=mysql

COPY --from=build /opt/shipping/target/shipping-1.0.jar shipping.jar
RUN curl -s -P /opt/shipping/ -OL https://github.com/DataDog/dd-trace-java/releases/download/v1.44.1/dd-java-agent.jar

CMD [ "java", "-XX:MaxRAMPercentage=75.0", "-javaagent:dd-java-agent.jar", "-jar", "shipping.jar" ]