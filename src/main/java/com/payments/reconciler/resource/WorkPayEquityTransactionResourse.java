package com.payments.reconciler.resource;

import com.payments.reconciler.entity.WorkPayEquityTransaction;
import com.payments.reconciler.repository.WorkPayEquityTransactionRepository;
import com.payments.reconciler.service.csvtodatabaseservice.CsvFileToBeanService;
import com.payments.reconciler.service.csvtodatabaseservice.CsvFileValidatorService;
import com.payments.reconciler.service.csvtodatabaseservice.SaveCsvFileToDatabaseService;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.multipart.MultipartFile;

import java.util.List;

/**
 * REST controller for handling equity bank statement upload in CSV format.
 * The controller provides an endpoint for uploading csv files containing equity bank statement data.
 * The data is then processed and stored in the database
 */
@RestController()
@RequestMapping("/api/upload")
public class WorkPayEquityTransactionResourse {

    private final Logger logger = LoggerFactory.getLogger(WorkPayEquityTransactionResourse.class);

    private final WorkPayEquityTransactionRepository repository;

    @Autowired
    private CsvFileValidatorService csvFileValidatorService;

    @Autowired
    private CsvFileToBeanService csvFileToBeanService;

    @Autowired
    private SaveCsvFileToDatabaseService saveCsvFileToDatabaseService;

    public WorkPayEquityTransactionResourse(WorkPayEquityTransactionRepository workPayEquityTransactionRepository) {
        this.repository = workPayEquityTransactionRepository;
    }

    @PostMapping("/workpay-equity")
    public String handleCsv(@RequestParam("workPayEquityStatement") MultipartFile file) throws Exception {

        try {
            //Validate uploaded CSV
            csvFileValidatorService.validate(file);

            //Get the list of all CSV transactions converted into JAVA beans
            List<WorkPayEquityTransaction> WorkPayEquityTransactionsBeans =
                    csvFileToBeanService.readToBean(file, WorkPayEquityTransaction.class);

            //Saving the JAVA beans into a database table
            saveCsvFileToDatabaseService.saveBeanTransactionsToDatabase(WorkPayEquityTransactionsBeans, repository);

        } catch (Exception e) {
            logger.warn(e.getMessage());
            throw new Exception(e);
        }

        return "File uploaded successfully";
    }
}









//Manual code

/*
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

    List<WorkPayEquityTransaction> WorkPayEquityTransactionsBeans = csvReader.parse();

try {
    repository.saveAll(WorkPayEquityTransactionsBeans);
    logger.info("Saved {} transactions to the database ", WorkPayEquityTransactionsBeans.size());
} catch (Exception e) {
    logger.error("Failed to save transactions to the database {}", e.getMessage());
    throw new RuntimeException("Error saving transactions to the database");
}
 */