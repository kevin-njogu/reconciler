package com.payments.reconciler.entity;

import com.opencsv.bean.CsvBindByName;
import com.opencsv.bean.CsvCustomBindByName;
import com.payments.reconciler.util.LocalDateConverterA;
import jakarta.persistence.*;

import java.time.LocalDate;

/**
 * Represents WorkPayEquity transaction entity in the application
 */
@Entity
public class WorkPayEquityTransaction {

    @Id
    @GeneratedValue(strategy = GenerationType.AUTO)
    private long id;

    @CsvCustomBindByName(column = "DATE", converter = LocalDateConverterA.class)
    @Column(nullable = false)
    private LocalDate transactionDate = LocalDate.now();

    @CsvBindByName(column = "Transaction ID")
    @Column(nullable = false)
    private String transactionId = "NA";

    @CsvBindByName(column = "API Reference")
    @Column(nullable = false)
    private String apiReference = "NA";

    @CsvBindByName(column = "PAYMENT METHOD")
    @Column(nullable = false)
    private String paymentMethod = "NA";

    @CsvBindByName(column = "ACCOUNT NO")
    @Column(nullable = false)
    private String accountNumber = "NA";

    @CsvBindByName(column = "CURRENCY")
    @Column(nullable = false)
    private String currency = "KES";

    @CsvBindByName(column = "AMOUNT")
    @Column(nullable = false)
    private double amount = 0.0;

    @CsvBindByName(column = "SENDER FEE")
    @Column(nullable = false)
    private double senderFee = 0.0;

    @CsvBindByName(column = "RECIPIENT FEE")
    @Column(nullable = false)
    private double recipientFee = 0.0;

    @CsvBindByName(column = "RECIPIENT")
    @Column(nullable = false)
    private String recipient = "NA";

    @CsvBindByName(column = "STATUS")
    @Column(nullable = false)
    private String status = "NA";

    @CsvBindByName(column = "REMARK")
    @Column(nullable = false)
    private String remark = "NA";

    @CsvBindByName(column = "RETRIES")
    @Column(nullable = false)
    private int retries = 0;

    @CsvBindByName(column = "COUNTRY")
    @Column(nullable = false)
    private String country= "NA";

    public WorkPayEquityTransaction() {}

    public WorkPayEquityTransaction(long id, LocalDate transactionDate, String transactionId, String apiReference,
                                    String paymentMethod, String accountNumber, String currency, double amount, double senderFee,
                                    double recipientFee, String recipient, String status, String remark, int retries, String country) {
        this.id = id;
        this.transactionDate = transactionDate;
        this.transactionId = transactionId;
        this.apiReference = apiReference;
        this.paymentMethod = paymentMethod;
        this.accountNumber = accountNumber;
        this.currency = currency;
        this.amount = amount;
        this.senderFee = senderFee;
        this.recipientFee = recipientFee;
        this.recipient = recipient;
        this.status = status;
        this.remark = remark;
        this.retries = retries;
        this.country = country;
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

    public String getTransactionId() {
        return transactionId;
    }

    public void setTransactionId(String transactionId) {
        this.transactionId = transactionId;
    }

    public String getApiReference() {
        return apiReference;
    }

    public void setApiReference(String apiReference) {
        this.apiReference = apiReference;
    }

    public String getPaymentMethod() {
        return paymentMethod;
    }

    public void setPaymentMethod(String paymentMethod) {
        this.paymentMethod = paymentMethod;
    }

    public String getAccountNumber() {
        return accountNumber;
    }

    public void setAccountNumber(String accountNumber) {
        this.accountNumber = accountNumber;
    }

    public String getCurrency() {
        return currency;
    }

    public void setCurrency(String currency) {
        this.currency = currency;
    }

    public double getAmount() {
        return amount;
    }

    public void setAmount(double amount) {
        this.amount = amount;
    }

    public double getSenderFee() {
        return senderFee;
    }

    public void setSenderFee(double senderFee) {
        this.senderFee = senderFee;
    }

    public double getRecipientFee() {
        return recipientFee;
    }

    public void setRecipientFee(double recipientFee) {
        this.recipientFee = recipientFee;
    }

    public String getRecipient() {
        return recipient;
    }

    public void setRecipient(String recipient) {
        this.recipient = recipient;
    }

    public String getStatus() {
        return status;
    }

    public void setStatus(String status) {
        this.status = status;
    }

    public String getRemark() {
        return remark;
    }

    public void setRemark(String remark) {
        this.remark = remark;
    }

    public int getRetries() {
        return retries;
    }

    public void setRetries(int retries) {
        this.retries = retries;
    }

    public String getCountry() {
        return country;
    }

    public void setCountry(String country) {
        this.country = country;
    }

    @Override
    public String toString() {
        return "WorkPayEquityTransaction{" +
                "id=" + id +
                ", transactionDate=" + transactionDate +
                ", transactionId='" + transactionId + '\'' +
                ", apiReference='" + apiReference + '\'' +
                ", paymentMethod='" + paymentMethod + '\'' +
                ", accountNumber='" + accountNumber + '\'' +
                ", currency='" + currency + '\'' +
                ", amount=" + amount +
                ", senderFee=" + senderFee +
                ", recipientFee=" + recipientFee +
                ", recipient='" + recipient + '\'' +
                ", status='" + status + '\'' +
                ", remark='" + remark + '\'' +
                ", retries=" + retries +
                ", country='" + country + '\'' +
                '}';
    }
}
