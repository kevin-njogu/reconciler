package com.payments.reconciler;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;


//This launches our app with an embedded Tomcat server
@SpringBootApplication
public class ReconcilerApplication {

	public static void main(String[] args) {
		SpringApplication.run(ReconcilerApplication.class, args);
	}

}
