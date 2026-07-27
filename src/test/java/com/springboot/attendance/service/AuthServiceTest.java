package com.springboot.attendance.service;

import com.springboot.attendance.dto.request.LoginRequest;
import com.springboot.attendance.dto.response.AuthResponse;
import com.springboot.attendance.entity.User;
import com.springboot.attendance.entity.UserRole;
import com.springboot.attendance.entity.UserSession;
import com.springboot.attendance.repository.UserRepository;
import com.springboot.attendance.repository.UserSessionRepository;
import com.springboot.attendance.security.JwtUtil;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.security.authentication.BadCredentialsException;
import org.springframework.security.crypto.password.PasswordEncoder;

import java.util.Optional;
import java.util.UUID;

import static org.assertj.core.api.Assertions.*;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.*;

@ExtendWith(MockitoExtension.class)
class AuthServiceTest {

    @Mock private UserRepository userRepository;
    @Mock private UserSessionRepository userSessionRepository;
    @Mock private JwtUtil jwtUtil;
    @Mock private PasswordEncoder passwordEncoder;
    @Mock private AuditLogService auditLogService;

    @InjectMocks
    private AuthService authService;

    private User mockUser;

    @BeforeEach
    void setUp() {
        mockUser = User.builder()
                .id(UUID.randomUUID())
                .username("admin")
                .passwordHash("hashedPassword")
                .role(UserRole.ADMIN)
                .build();
        mockUser.setActive(true);
    }

    @Test
    void login_success() {
        var req = new LoginRequest();
        req.setUsername("admin");
        req.setPassword("changeme");

        when(userRepository.findByUsername("admin")).thenReturn(Optional.of(mockUser));
        when(passwordEncoder.matches("changeme", "hashedPassword")).thenReturn(true);
        when(jwtUtil.generateAccessToken(any(), any(), any())).thenReturn("access-token");
        when(jwtUtil.generateRefreshToken(any())).thenReturn("refresh-token");
        when(jwtUtil.getRefreshTokenExpiry()).thenReturn(604800L);
        when(userSessionRepository.save(any())).thenReturn(new UserSession());
        when(userRepository.save(any())).thenReturn(mockUser);

        AuthResponse res = authService.login(req, "127.0.0.1", "PostmanTest");

        assertThat(res.getAccessToken()).isEqualTo("access-token");
        assertThat(res.getRefreshToken()).isEqualTo("refresh-token");
        assertThat(res.getRole()).isEqualTo("ADMIN");
        assertThat(res.getUsername()).isEqualTo("admin");
    }

    @Test
    void login_wrongPassword_throwsBadCredentials() {
        var req = new LoginRequest();
        req.setUsername("admin");
        req.setPassword("wrong");

        when(userRepository.findByUsername("admin")).thenReturn(Optional.of(mockUser));
        when(passwordEncoder.matches("wrong", "hashedPassword")).thenReturn(false);

        assertThatThrownBy(() -> authService.login(req, "127.0.0.1", "test"))
                .isInstanceOf(BadCredentialsException.class)
                .hasMessage("Invalid credentials");
    }

    @Test
    void login_userNotFound_throwsBadCredentials() {
        var req = new LoginRequest();
        req.setUsername("unknown");
        req.setPassword("password");

        when(userRepository.findByUsername("unknown")).thenReturn(Optional.empty());

        assertThatThrownBy(() -> authService.login(req, "127.0.0.1", "test"))
                .isInstanceOf(BadCredentialsException.class)
                .hasMessage("Invalid credentials");
    }

    @Test
    void login_inactiveUser_throwsBadCredentials() {
        mockUser.setActive(false);
        var req = new LoginRequest();
        req.setUsername("admin");
        req.setPassword("changeme");

        when(userRepository.findByUsername("admin")).thenReturn(Optional.of(mockUser));

        assertThatThrownBy(() -> authService.login(req, "127.0.0.1", "test"))
                .isInstanceOf(BadCredentialsException.class)
                .hasMessage("Account is disabled");
    }
}