package com.example.keycloak.spi;

import org.keycloak.Config;
import org.keycloak.authentication.Authenticator;
import org.keycloak.authentication.AuthenticatorFactory;
import org.keycloak.models.AuthenticationExecutionModel;
import org.keycloak.models.KeycloakSession;
import org.keycloak.models.KeycloakSessionFactory;
import org.keycloak.provider.ProviderConfigProperty;

import java.util.Collections;
import java.util.List;

/**
 * LastLoginTrackerAuthenticator の Factory
 * Meta-INF/services 経由で Keycloak に登録される
 */
public class LastLoginTrackerAuthenticatorFactory implements AuthenticatorFactory {

    public static final String PROVIDER_ID = "last-login-tracker";

    private static final LastLoginTrackerAuthenticator SINGLETON = new LastLoginTrackerAuthenticator();

    @Override
    public String getId() {
        return PROVIDER_ID;
    }

    @Override
    public Authenticator create(KeycloakSession session) {
        return SINGLETON;
    }

    @Override
    public String getDisplayType() {
        return "Last Login Tracker";
    }

    @Override
    public String getHelpText() {
        return "Writes last_login user_attribute on successful authentication. " +
               "Debounces updates to once per day for performance.";
    }

    @Override
    public String getReferenceCategory() {
        return "last-login";
    }

    @Override
    public boolean isConfigurable() {
        return false;
    }

    @Override
    public AuthenticationExecutionModel.Requirement[] getRequirementChoices() {
        return new AuthenticationExecutionModel.Requirement[]{
            AuthenticationExecutionModel.Requirement.REQUIRED,
            AuthenticationExecutionModel.Requirement.ALTERNATIVE,
            AuthenticationExecutionModel.Requirement.DISABLED
        };
    }

    @Override
    public boolean isUserSetupAllowed() {
        return false;
    }

    @Override
    public List<ProviderConfigProperty> getConfigProperties() {
        return Collections.emptyList();
    }

    @Override
    public void init(Config.Scope config) {
        // 初期化不要
    }

    @Override
    public void postInit(KeycloakSessionFactory factory) {
        // 初期化不要
    }

    @Override
    public void close() {
        // クリーンアップ不要
    }
}
