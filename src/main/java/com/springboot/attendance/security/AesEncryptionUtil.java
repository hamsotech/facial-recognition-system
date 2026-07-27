package com.springboot.attendance.security;

import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Component;

import javax.crypto.Cipher;
import javax.crypto.spec.GCMParameterSpec;
import javax.crypto.spec.SecretKeySpec;
import java.security.SecureRandom;
import java.util.Base64;

@Component
public class AesEncryptionUtil {

    private static final String ALGO = "AES/GCM/NoPadding";
    private static final int GCM_IV_LENGTH = 12;
    private static final int GCM_TAG_LENGTH = 128;

    private final SecretKeySpec keySpec;

    public AesEncryptionUtil(@Value("${encryption.secret-key}") String base64Key) {
        byte[] decoded = Base64.getDecoder().decode(base64Key);
        this.keySpec = new SecretKeySpec(decoded, "AES");
    }

    public byte[] encrypt(byte[] plainData) {
        try {
            byte[] iv = new byte[GCM_IV_LENGTH];
            new SecureRandom().nextBytes(iv);

            Cipher cipher = Cipher.getInstance(ALGO);
            cipher.init(Cipher.ENCRYPT_MODE, keySpec, new GCMParameterSpec(GCM_TAG_LENGTH, iv));

            byte[] cipherText = cipher.doFinal(plainData);

            byte[] result = new byte[iv.length + cipherText.length];
            System.arraycopy(iv, 0, result, 0, iv.length);
            System.arraycopy(cipherText, 0, result, iv.length, cipherText.length);

            return result;
        } catch (Exception e) {
            throw new RuntimeException("Failed to encrypt embedding", e);
        }
    }

    public byte[] decrypt(byte[] encryptedData) {
        try {
            byte[] iv = new byte[GCM_IV_LENGTH];
            byte[] cipherText = new byte[encryptedData.length - GCM_IV_LENGTH];

            System.arraycopy(encryptedData, 0, iv, 0, iv.length);
            System.arraycopy(encryptedData, GCM_IV_LENGTH, cipherText, 0, cipherText.length);

            Cipher cipher = Cipher.getInstance(ALGO);
            cipher.init(Cipher.DECRYPT_MODE, keySpec, new GCMParameterSpec(GCM_TAG_LENGTH, iv));

            return cipher.doFinal(cipherText);
        } catch (Exception e) {
            throw new RuntimeException("Failed to decrypt embedding", e);
        }
    }
}