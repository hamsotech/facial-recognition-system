package com.springboot.attendance.dto.response;

import lombok.Builder;
import lombok.Getter;

import java.time.OffsetDateTime;
import java.util.UUID;

@Getter @Builder
public class UserResponse {
    private UUID id;
    private String username;
    private String fullName;
    private String email;
    private String role;
    private boolean isActive;
    private OffsetDateTime lastLoginAt;
    private OffsetDateTime createdAt;
}