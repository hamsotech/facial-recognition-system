package com.springboot.attendance.dto.request;

import com.springboot.attendance.entity.UserRole;
import jakarta.validation.constraints.Email;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.Size;
import lombok.Getter;
import lombok.Setter;

@Getter @Setter
public class UserRequest {
    @NotBlank
    @Size(max = 50)
    private String username;

    @NotBlank
    @Size(min = 8, max = 255)
    private String password;

    @Size(max = 100)
    private String fullName;

    @Email
    @Size(max = 100)
    private String email;

    @NotNull
    private UserRole role;
}