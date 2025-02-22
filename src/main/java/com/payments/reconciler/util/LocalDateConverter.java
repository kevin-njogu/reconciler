package com.payments.reconciler.util;

import com.opencsv.bean.AbstractBeanField;
import com.opencsv.exceptions.CsvConstraintViolationException;
import com.opencsv.exceptions.CsvDataTypeMismatchException;

import java.time.LocalDate;
import java.time.format.DateTimeFormatter;
import java.time.format.DateTimeParseException;

/**
 *This class is custom converter for opencsv that converts
 *a String date in the format of "dd-MM-yyyy" into a LocalDate Object.
 *It extends AbstractBeanField which facilitates automatic conversion while parsing CSV files.
 */
public class LocalDateConverter extends AbstractBeanField<LocalDate, String> {

    //Defining a DateTimeFormatter to parse date Strings that come in the format "dd-MM-yyyy"
    private static final DateTimeFormatter formatter = DateTimeFormatter.ofPattern("dd-MM-yyyy");

    /**
     * Convert a date string coming in from the CSV into a LocalDate object.
     *
     * @param dateString The date String from the CSV file.
     * @return The Corresponding LocalDate object.
     * @throws CsvDataTypeMismatchException Exception thrown when the provided dateString value for conversion cannot be
     * converted to the required type of the destination field.
     * @throws CsvConstraintViolationException exception is thrown when logical connections between
     * data fields would be violated by the imported data
     * @throws DateTimeParseException An exception thrown when an error occurs during parsing.
     */
    @Override
    protected LocalDate convert(String dateString)
            throws CsvDataTypeMismatchException, CsvConstraintViolationException, DateTimeParseException {
        return LocalDate.parse(dateString, formatter);
    }



    /**
     * Convert a date string coming in from the CSV into a LocalDate object.
     *
     * @param value
     * @return
     */
//    @Override
//    protected LocalDate convert(String value) {
//        return LocalDate.parse(value, formatter);
//    }
}
