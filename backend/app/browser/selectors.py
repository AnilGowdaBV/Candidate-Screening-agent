"""Selector definitions and URL constants for Instahyre automation."""

# URLs
INSTAHYRE_BASE_URL = "https://www.instahyre.com"
INSTAHYRE_LOGIN_URL = "https://www.instahyre.com/login/"

# Authentication Selectors
AUTH_SELECTORS = {
    "email_input": 'input[type="email"], input[name="email"], input#email',
    "password_input": 'input[type="password"], input[name="password"], input#password',
    "submit_button": 'button[type="submit"], input[type="submit"], button:has-text("Log in"), button:has-text("Sign in")',
    "logged_in_indicator": '.user-profile, .employer-nav, a[href*="/employer/"], .profile-avatar, button:has-text("Logout"), a:has-text("Logout")',
    "login_form": 'form#login-form, form[action*="login"], form',
    "captcha_indicator": 'iframe[src*="captcha"], iframe[src*="recaptcha"], iframe[src*="cloudflare"], div.g-recaptcha',
}

# Search Page Selectors
SEARCH_SELECTORS = {
    "search_container": '#candidate-search-results, .candidates-list, .search-results, .list-view',
    "candidate_cards": '.candidate-row, .ats-resume-profile',
    "candidate_link": '.candidate-row, a[href*="/candidate/"]',
    "candidate_name": '.candidate-name .readonly-field, .candidate-name, h3, h4',
    "view_profile_button": '.button-download-resume, a:has-text("View profile")',
    "pagination_next": 'a:has-text("Next"), button:has-text("Next"), li.next a, a[rel="next"]',
    "no_results": ':has-text("No candidates found"), :has-text("No results")',
}

# Candidate Profile Selectors
PROFILE_SELECTORS = {
    "name": '.candidate-name .readonly-field, .candidate-name, h1, h2, .name',
    "external_id_meta": '[data-candidate-id], [data-external-id], input[name="candidate_id"]',
    "github_link": 'a[href*="github.com"]',
    "social_links_container": '.social-links, .links-section, .candidate-links, .profile-links',
    "resume_links": 'a[href*="resume"], a[href*=".pdf"], a:has-text("Resume")',
    
    # Notes Section inside Modal
    "notes_tab_or_button": 'a:has-text("Notes"), button:has-text("Notes"), [ng-click*="notifyNotes"]',
    "notes_container": '#notes-tab, .notes-block, .existing-notes',
    "single_note": '#notes-tab .note-message, #notes-tab .single-note, #notes-tab .message-body, #notes-tab [class*="note-text"], .note-item',
    "note_editor": '#notes-tab .ql-editor, .ql-editor, textarea[name="note"], textarea',
    "note_textarea": '#notes-tab .ql-editor, textarea[name="note"], textarea',
    "note_save_button": '#notes-tab button.add-note-btn, button.add-note-btn, button:has-text("Add note"), button:has-text("Save")',
    "modal_close": '.application-modal-close, .back-button-modal-close, [ng-click*="closeModal"], i.fa-close, .close',
}
