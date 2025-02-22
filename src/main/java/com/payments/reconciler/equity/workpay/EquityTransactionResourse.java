package com.payments.reconciler.equity.workpay;

import com.opencsv.bean.CsvToBean;
import com.opencsv.bean.CsvToBeanBuilder;
import com.opencsv.exceptions.CsvException;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.multipart.MultipartFile;

import java.io.IOException;
import java.io.InputStreamReader;
import java.io.Reader;
import java.nio.charset.StandardCharsets;
import java.util.List;
import java.util.Objects;


/**
 * REST controller for handling equity bank statement upload in CSV format.
 * The controller provides an endpoint for uploading csv files containing equity bank statement data.
 * The data is then processed and stored in the database
 */
@RestController()
@RequestMapping("/api/files")
public class EquityTransactionResourse {

    private final Logger logger = LoggerFactory.getLogger(EquityTransactionResourse.class);
    private final EquityTransactionRepository repository;

    //Constructor injection for the repository interface
    public EquityTransactionResourse(EquityTransactionRepository repository) {
        this.repository = repository;
    }

    /**
     * Handles CSV file uploads containing Equity bank transactions.
     *
     * @param file the CSV file uploaded by the client.
     * @throws IOException if an I/O error occurs while reading the file.
     * @throws CsvException if the file is missing, has an invalid format, or contains parsing errors.
     * The method validates the uploaded file, ensuring it is not empty and is of the correct file type.
     * It then parses the CSV contents into EquityTransaction objects and saves them to the database.
     */
    @PostMapping("/equity-bank")
    public String handleCsv(@RequestParam("equityBankStatement") MultipartFile file) throws IOException, CsvException {

        String ALLOWED_FILE_EXTENSION = "text/csv";

        if (file.isEmpty()) {
            logger.warn("Uploaded file is empty");
            throw  new CsvException("Equity bank statement not found");
        }

        if (!Objects.equals(file.getContentType(), ALLOWED_FILE_EXTENSION)) {
            logger.warn("Invalid file type {}", file.getContentType());
            throw new CsvException("Invalid filetype");
        }

        try(Reader reader = new InputStreamReader(file.getInputStream(), StandardCharsets.UTF_8)){

            CsvToBean<WorkPayEquityTransaction> csvReader = new CsvToBeanBuilder<WorkPayEquityTransaction>(reader)
                    .withType(WorkPayEquityTransaction.class)
                    .withSeparator(',')
                    .withIgnoreLeadingWhiteSpace(true)
                    .build();

            List<WorkPayEquityTransaction> equityTransactionsBeans = csvReader.parse();

            try {
                repository.saveAll(equityTransactionsBeans);
                logger.info("Saved {} transactions to the database ", equityTransactionsBeans.size());
            } catch (Exception e) {
                logger.error("Failed to save transactions to the database {}", e.getMessage());
                throw new RuntimeException("Error saving transactions to the database");
            }
        }
        return "File uploaded successfully";
    }
}
