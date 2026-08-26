package com.xinghe.business.exception;

import jakarta.servlet.FilterChain;
import jakarta.servlet.ServletException;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import org.springframework.stereotype.Component;
import org.springframework.web.filter.OncePerRequestFilter;

import java.io.IOException;
import java.util.UUID;

@Component
public class RequestTraceFilter extends OncePerRequestFilter {
    public static final String TRACE_ID = "xinghe.traceId";

    @Override
    protected void doFilterInternal(HttpServletRequest request, HttpServletResponse response,
                                    FilterChain filterChain) throws ServletException, IOException {
        String traceId = request.getHeader("X-Request-ID");
        if (traceId == null || traceId.isBlank() || traceId.length() > 80) {
            traceId = "req_" + UUID.randomUUID().toString().replace("-", "");
        }
        request.setAttribute(TRACE_ID, traceId);
        response.setHeader("X-Request-ID", traceId);
        filterChain.doFilter(request, response);
    }
}
