FROM eclipse-temurin:17-jre
WORKDIR /app
COPY target/business-service-0.1.0-SNAPSHOT.jar app.jar
EXPOSE 8081
ENTRYPOINT ["java", "-jar", "app.jar"]
