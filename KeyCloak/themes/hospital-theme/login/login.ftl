<#import "template.ftl" as layout>
<@layout.registrationLayout displayMessage=false; section>
    <#if section = "header">
        <div class="hospital-header">
            <div class="hospital-logo">
                <svg class="hospital-icon" viewBox="0 0 24 24" fill="currentColor">
                    <path d="M12 2L2 7v10l10 5 10-5V7L12 2zm0 2.9l6.9 3.45L12 12 5.1 8.35 12 4.9zm0 13.1l-7-3.5V9.3l7 3.5 7-3.5v5.2l-7 3.5z"/>
                </svg>
                <h1 class="hospital-title">MediCare Hospital</h1>
                <p class="hospital-subtitle">Role-Based Access System</p>
                <p class="hospital-instruction">Sign in with your assigned role</p>
            </div>
        </div>
    <#elseif section = "form">
        <#if realm.password>
            <form id="kc-form-login" onsubmit="login.disabled = true; return true;" action="${url.loginAction}" method="post">
                <div class="form-group">
                    <label for="username" class="form-label">
                        <#if !realm.loginWithEmailAllowed>
                            ${msg("username")}
                        <#elseif !realm.registrationEmailAsUsername>
                            ${msg("usernameOrEmail")}
                        <#else>
                            ${msg("email")}
                        </#if>
                    </label>
                    <input tabindex="1" id="username" class="form-input" 
                           name="username" value="${(login.username!'')}" 
                           type="text" autofocus autocomplete="off" 
                           placeholder="Enter username or email" />
                </div>

                <div class="form-group">
                    <label for="password" class="form-label">${msg("password")}</label>
                    <input tabindex="2" id="password" class="form-input" 
                           name="password" type="password" autocomplete="off" 
                           placeholder="Enter password" />
                </div>

                <#if realm.rememberMe && !usernameEditDisabled??>
                <div class="remember-me">
                    <input tabindex="3" id="rememberMe" name="rememberMe" type="checkbox" />
                    <label for="rememberMe">${msg("rememberMe")}</label>
                </div>
                </#if>

                <#if message?has_content>
                <div class="alert alert-${message.type}">
                    <span class="alert-icon">!</span>
                    <span class="alert-text">${message.summary}</span>
                </div>
                </#if>

                <div id="kc-form-buttons" class="form-actions">
                    <input tabindex="4" class="btn btn-primary btn-block" 
                           name="login" id="kc-login" type="submit" 
                           value="${msg("doLogIn")}" />
                </div>
            </form>
        </#if>
        
        <#if realm.password && realm.registrationAllowed && !registrationDisabled??>
        <div class="register-link">
            <span>${msg("noAccount")} <a href="${url.registrationUrl}">${msg("doRegister")}</a></span>
        </div>
        </#if>
    </#if>
</@layout.registrationLayout>