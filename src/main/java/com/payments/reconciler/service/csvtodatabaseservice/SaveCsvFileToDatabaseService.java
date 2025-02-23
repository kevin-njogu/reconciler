package com.payments.reconciler.service.csvtodatabaseservice;

import com.payments.reconciler.resource.EquityTransactionResourse;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Service;

import java.util.List;

@Service
public class SaveCsvFileToDatabaseService {

    private final Logger logger = LoggerFactory.getLogger(SaveCsvFileToDatabaseService.class);

    public <T> void saveBeanTransactionsToDatabase (
            List<T> transactions, JpaRepository<T, Long> repository) throws Exception {

        try {
            repository.saveAll(transactions);
        } catch (Exception e) {
            logger.warn(e.getMessage());
            throw new Exception("Error saving transactions to the database");
        }
    }

}
