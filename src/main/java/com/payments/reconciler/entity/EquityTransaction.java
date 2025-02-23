package com.payments.reconciler.entity;

import com.opencsv.bean.CsvBindByName;
import com.opencsv.bean.CsvCustomBindByName;
import com.payments.reconciler.util.LocalDateConverter;
import jakarta.persistence.*;

import java.time.LocalDate;

/**
 * Represents Equity transaction entity in the application
 */
@Entity
public class EquityTransaction {

    @Id
    @GeneratedValue(strategy = GenerationType.AUTO)
    private long id;

    @CsvCustomBindByName(column = "Transaction Date", converter = LocalDateConverter.class)
    @Column(nullable = true)
    private LocalDate transactionDate = LocalDate.now();

    @CsvCustomBindByName(column = "Value Date", converter = LocalDateConverter.class)
    @Column(nullable = true)
    private LocalDate valueDate = LocalDate.now();

    @CsvBindByName(column = "Narrative")
    @Column(nullable = true)
    private String narrative = "NA";

    @CsvBindByName(column = "Debit")
    @Column(nullable = true)
    private double debitAmount = 0.0;

    @CsvBindByName(column = "Credit")
    @Column(nullable = true)
    private double creditAmount = 0.0;

    @CsvBindByName(column = "Running Balance")
    @Column(nullable = true)
    private double accountBalance = 0.0;

    public EquityTransaction() {
    }

    public EquityTransaction(long id, LocalDate transactionDate, LocalDate valueDate, String narrative,
                             double debitAmount, double creditAmount, double accountBalance) {
        this.id = id;
        this.transactionDate = transactionDate;
        this.valueDate = valueDate;
        this.narrative = narrative;
        this.debitAmount = debitAmount;
        this.creditAmount = creditAmount;
        this.accountBalance = accountBalance;
    }

    public long getId() {
        return id;
    }

    public void setId(long id) {
        this.id = id;
    }

    public LocalDate getTransactionDate() {
        return transactionDate;
    }

    public void setTransactionDate(LocalDate transactionDate) {
        this.transactionDate = transactionDate;
    }

    public LocalDate getValueDate() {
        return valueDate;
    }

    public void setValueDate(LocalDate valueDate) {
        this.valueDate = valueDate;
    }

    public String getNarrative() {
        return narrative;
    }

    public void setNarrative(String narrative) {
        this.narrative = narrative;
    }

    public double getDebitAmount() {
        return debitAmount;
    }

    public void setDebitAmount(double debitAmount) {
        this.debitAmount = debitAmount;
    }

    public double getCreditAmount() {
        return creditAmount;
    }

    public void setCreditAmount(double creditAmount) {
        this.creditAmount = creditAmount;
    }

    public double getAccountBalance() {
        return accountBalance;
    }

    public void setAccountBalance(double accountBalance) {
        this.accountBalance = accountBalance;
    }

    @Override
    public String toString() {
        return "EquityTransaction{" +
                "id=" + id +
                ", transactionDate=" + transactionDate +
                ", valueDate=" + valueDate +
                ", narrative='" + narrative + '\'' +
                ", debitAmount=" + debitAmount +
                ", creditAmount=" + creditAmount +
                ", accountBalance=" + accountBalance +
                '}';
    }
}
