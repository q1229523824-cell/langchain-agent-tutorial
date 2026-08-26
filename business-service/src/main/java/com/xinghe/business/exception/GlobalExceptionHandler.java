package com.xinghe.business.exception;

import jakarta.servlet.http.HttpServletRequest;
import jakarta.validation.ConstraintViolationException;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.MethodArgumentNotValidException;
import org.springframework.web.bind.annotation.ExceptionHandler;
import org.springframework.web.bind.annotation.RestControllerAdvice;

import java.util.Map;

@RestControllerAdvice
public class GlobalExceptionHandler {
    @ExceptionHandler(BusinessException.class)
    ResponseEntity<?> business(BusinessException ex, HttpServletRequest request) {
        return ResponseEntity.status(ex.getHttpStatus()).body(error(ex.getCode(), ex.getMessage(), request));
    }

    @ExceptionHandler({MethodArgumentNotValidException.class, ConstraintViolationException.class})
    ResponseEntity<?> validation(Exception ex, HttpServletRequest request) {
        return ResponseEntity.badRequest().body(error("VALIDATION_ERROR", "请求参数校验失败", request));
    }

    private Map<String, Object> error(String code, String message, HttpServletRequest request) {
        return Map.of("error", Map.of("code", code, "message", message),
                "traceId", request.getAttribute(RequestTraceFilter.TRACE_ID));
    }
}
