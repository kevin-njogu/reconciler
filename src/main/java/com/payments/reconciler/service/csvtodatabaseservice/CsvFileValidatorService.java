package com.payments.reconciler.service.csvtodatabaseservice;

import com.opencsv.exceptions.CsvException;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Service;
import org.springframework.web.multipart.MultipartFile;

import java.util.Objects;

@Service
public class CsvFileValidatorService {

    private final Logger logger = LoggerFactory.getLogger(CsvFileValidatorService.class);

    public void validate(MultipartFile file) throws CsvException {
        String ALLOWED_FILE_EXTENSION = "text/csv";

        try {
            if (file.isEmpty()) {
                throw new CsvException("Equity bank statement not found");
            }

            if (!Objects.equals(file.getContentType(), ALLOWED_FILE_EXTENSION)) {
                throw new CsvException("Invalid filetype");
            }
        }catch (CsvException e) {
            logger.warn(e.getMessage());
            throw new RuntimeException(e.getMessage());
        }
    }
}
