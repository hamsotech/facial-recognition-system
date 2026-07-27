package com.springboot.attendance.security;

import jakarta.servlet.FilterChain;
import jakarta.servlet.ServletException;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Component;
import org.springframework.web.filter.OncePerRequestFilter;

import java.io.IOException;

@Component
public class InternalApiKeyFilter extends OncePerRequestFilter {

    @Value("${internal.api-key}")
    private String apiKey;

    @Override
    protected void doFilterInternal(HttpServletRequest req, HttpServletResponse res, FilterChain chain) throws ServletException, IOException {
        if (!req.getRequestURI().startsWith("/internal/")) {
            chain.doFilter(req, res);
            return;
        }

        String key = req.getHeader("X-Internal-Api-Key");
        if (key == null || !key.equals(apiKey)) {
            res.setStatus(HttpServletResponse.SC_UNAUTHORIZED);
            res.getWriter().write("{\"message\":\"Invalid internal API key\"}");
            return;
        }

        chain.doFilter(req, res);
    }
}