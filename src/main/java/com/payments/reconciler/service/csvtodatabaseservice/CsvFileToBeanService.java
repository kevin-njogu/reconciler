package com.payments.reconciler.service.csvtodatabaseservice;

import com.opencsv.bean.CsvToBean;
import com.opencsv.bean.CsvToBeanBuilder;
import org.springframework.stereotype.Service;
import org.springframework.web.multipart.MultipartFile;

import java.io.IOException;
import java.io.InputStreamReader;
import java.io.Reader;
import java.nio.charset.StandardCharsets;
import java.util.List;

/**
 * CsvFileToBeanService is a utility class for converting CSV files rows into Java objects (beans).
 * It leverages the OpenCSV library to parse CSV files and map their contents to a list of
 * objects of the specified entity class.
 *
 * @author kevin
 */

@Service
public class CsvFileToBeanService {

    //The entityClass is a Class<T> object, meaning it represents a class that follows JavaBean conventions
    public <T> List<T> readToBean(MultipartFile file, Class<T> entityClass) {

        try (Reader reader = new InputStreamReader(file.getInputStream(), StandardCharsets.UTF_8)) {

            CsvToBean<T> csvReader = new CsvToBeanBuilder<T>(reader)
                    .withType(entityClass) //This tells OpenCSV that each row in the CSV should be converted into an instance of the specified class entity class
                    .withSeparator(',')
                    .withIgnoreLeadingWhiteSpace(true)
                    .build();

            List<T> transactions = csvReader.parse();
            return transactions;
        } catch (IOException e) {
            throw new RuntimeException("Failed to convert file to bean", e);
        }
    }
}
