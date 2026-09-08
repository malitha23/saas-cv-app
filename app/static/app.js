function resumeApp() {
  return {
    // State
    resumeText: '',
    jobDescription: '',
    targetJobTitle: '',
    targetCompany: '',
    roleArchetype: 'auto',
    coverLetterTone: 'professional',
    currentTemplate: 'classic',
    portfolioTheme: 'bento_grid',
    portfolioAccent: '#6366f1',
    portfolioFont: 'Inter',
    fileName: '',
    extractedCandidateName: '',
    dragOver: false,
    isUploading: false,
    isTailoring: false,
    isDownloading: false,
    isPublishing: false,
    tailorStatusText: 'Analyzing keywords & extracting real achievements...',
    showRawText: false,
    showApiModal: false,
    showPricingModal: false,
    showDomainModal: false,
    customDomainInput: '',
    editorTab: 'resume', // 'resume', 'design', 'cover_letter', 'portfolio'
    userApiKey: '',
    activeTab: 'resume', // 'resume', 'cover_letter', 'portfolio', 'text', 'jobs'
    tailoredData: null,
    pdfBlobUrl: null,
    pdfBlobKey: 0,
    portfolioHtml: '',
    publishedLiveUrl: '',
    sampleData: {},
    sampleJD: '',
    copied: false,
    debounceTimer: null,
    darkMode: true,
    newSkillInputs: {},

    // SaaS Auth & MySQL Cloud State
    currentUser: null,
    avatarImgFailed: false,
    showUserProfileDropdown: false,
    showAuthModal: false,
    authMode: 'login', // 'login' or 'register'
    authPromptMessage: '',
    pendingAction: null,
    authForm: { email: '', password: '', full_name: '' },
    authError: '',
    isSubmittingAuth: false,
    googleClientId: '',
    isGoogleAuthEnabled: false,
    isSubmittingGoogleAuth: false,
    isGoogleButtonRendered: false,
    showSavedResumesModal: false,
    userSavedResumes: [],
    isSavingResume: false,
    isLoadingSavedResumes: false,

    // AI Job Hunter, Application Copilot & Tracker State
    jobSubTab: 'recommendations', // 'recommendations', 'hunter', 'tracker'
    jobSearchQuery: { keywords: '', location: 'Remote', work_mode: 'all', experience_level: 'all' },
    jobSearchResults: [],
    isSearchingJobs: false,
    showCopilotModal: false,
    currentCopilotJob: null,
    copilotKit: null,
    isLoadingCopilot: false,
    copiedKey: '',
    userTrackedJobs: [],
    isLoadingTrackedJobs: false,

    // AI Career Copilot Chatbot State
    showChatBot: false,
    chatMessages: [],
    chatInput: '',
    isChatLoading: false,
    suggestedPrompts: [
      'Conduct a realistic technical mock interview for my role',
      'Critique my resume bullets with the Google XYZ formula',
      'Draft a personalized LinkedIn DM to a hiring manager',
      'Give me a strategic salary negotiation script'
    ],

    // AI Voice Mock Interview Studio State
    voiceInterviewModalOpen: false,
    interviewStep: 'setup', // 'setup', 'interviewing', 'critique', 'final_report'
    interviewTargetRole: '',
    interviewTargetCompany: '',
    interviewType: 'behavioral', // 'behavioral', 'technical', 'situational'
    interviewDifficulty: 'standard', // 'friendly', 'standard', 'executive'
    interviewQuestionCount: 3,
    interviewQuestions: [],
    currentQuestionIndex: 0,
    interviewSessionId: '',
    currentQuestion: null,
    isStartingInterview: false,
    isInterviewerSpeaking: false,
    isRecordingAnswer: false,
    candidateAnswerTranscript: '',
    recordingDurationSeconds: 0,
    recordingTimerInterval: null,
    speechRecognitionInstance: null,
    showManualTextInput: false,
    isEvaluatingAnswer: false,
    currentEvaluation: null,
    sessionEvaluations: [],
    finalReport: null,

    // Real-Time AI Video Conference & Live Mistake Coaching State
    realtimeConferenceOpen: false,
    conferenceSessionId: '',
    conferenceTargetRole: 'Automotive Technician',
    conferenceTargetCompany: '',
    conferenceDurationSeconds: 0,
    conferenceTimerInterval: null,
    isCameraOn: true,
    isMicMuted: false,
    isAiSpeakingTurn: false,
    isAiThinking: false,
    isCandidateSpeaking: false,
    conferenceSilenceTimer: null,
    liveCoachingEnabled: true,
    activeCoachingNudge: null,
    liveSubtitleSpeaker: '',
    liveSubtitleText: '',
    conferenceSidebarOpen: false,
    conferenceConversationHistory: [],
    conferenceMistakes: [],
    candidateStream: null,
    conferenceSpeechRecognition: null,
    conferenceDebriefModalOpen: false,
    conferenceDebriefData: null,

    // Pro Restore Modal State (Replacing browser alert)
    showProRestoreModal: false,
    pendingRestoreResume: null,

    // In-App Logout Confirmation Modal State
    showLogoutModal: false,

    // In-App Welcome & Success Modal State
    showWelcomeModal: false,
    welcomeModalData: { title: '', message: '' },

    // In-App Quota Limit & Feature Lock Modal State
    showQuotaLimitModal: false,
    quotaLimitData: { title: '', message: '', feature: '', requiredPlan: 'pro' },

    // In-App Legal & Compliance Modal State
    showLegalModal: false,
    activeLegalTab: 'privacy',

    // Interactive Quota Dropdown Popover in Header
    showQuotaDropdown: false,

    // Dynamic Subscription Plans & Country-Specific Pricing State
    activeCountryCode: 'LK',
    activeCurrency: 'LKR',
    activeCurrencySymbol: 'Rs.',
    activeSprintPrice: 'Rs. 490',
    availableCountries: [
      { code: 'LK', name: 'Sri Lanka', currency: 'LKR', symbol: 'Rs.' },
      { code: 'DEFAULT', name: 'Global', currency: 'USD', symbol: '$' }
    ],
    dynamicPlans: [
      {
        plan_key: "free",
        title: "Free Starter",
        badge: "Freemium",
        price_display: "$0",
        period_display: "/ forever",
        sub_billing_text: "",
        description: "Great for trying out AI resume keyword tailoring.",
        features: [
          "2 AI Tailored Runs per day",
          "ATS Keyword Match & Score",
          "Classic ATS Resume Format (2 Lifetime Free Downloads)",
          "Visual Photo CV Formats (1 Lifetime Free Download)",
          "3 AI Cover Letters (1st Clean • 2nd & 3rd Watermarked)",
          "Interactive Web Portfolio Studio (Preview & Test • Live Hosting requires Pro)",
          "MySQL Cloud Auto-Save (Included • Pro required to load/restore)"
        ],
        is_popular: false,
        button_text: "Current Plan"
      },
      {
        plan_key: "pro",
        title: "Pro Career",
        badge: "🔥 Best Seller",
        price_display: "$9",
        period_display: "/ month",
        sub_billing_text: "or $19 for 3-Month Job Hunt Pass",
        description: "Everything needed to land senior interviews with confidence.",
        features: [
          "Unlimited AI Tailoring runs",
          "All 4 Visual CV Formats (High-Res Download)",
          "Unlimited AI Cover Letters (100% Watermark-Free & Clean)",
          "Photo & Digital Signature Upload",
          "Hosted Live Portfolio Subdomain (.dreemfolio.com)",
          "MySQL Cloud Auto-Save & Revision Archive"
        ],
        is_popular: true,
        button_text: "Upgrade to Pro ($9/mo)"
      },
      {
        plan_key: "elite",
        title: "Executive Elite",
        badge: "Personal Brand",
        price_display: "$19",
        period_display: "/ month",
        sub_billing_text: "",
        description: "For Tech Leads, Architects & Executives building an elite digital brand.",
        features: [
          "Everything in Pro Career",
          "All 8 Portfolio Web Architectures",
          "100% Full CRUD Portfolio Studio",
          "Connect Custom Private Domain & SSL",
          "Standalone Website HTML Export",
          "Priority AI Processing Queue"
        ],
        is_popular: false,
        button_text: "Upgrade to Elite ($19/mo)"
      }
    ],

    // Admin Dashboard State
    showAdminModal: false,
    adminActiveTab: 'overview',
    isLoadingAdminOverview: false,
    adminOverview: null,
    adminSettingsState: {
      free_daily_ai_limit: 2,
      free_daily_pdf_limit: 1,
      free_allow_visual_download: false,
      free_allow_cloud_restore: false,
      pro_monthly_price: 9,
      elite_monthly_price: 29,
      sprint_price: 3
    },
    isSavingAdminSettings: false,
    adminSettingsSaveMsg: '',
    adminUsersList: [],
    adminUserSearchQuery: '',
    isLoadingAdminUsers: false,

    // Real-Time MySQL Auto-Save State
    currentResumeId: null,
    autoSaveStatus: 'saved', // 'saved', 'saving', 'unsaved', 'error'
    lastSavedTime: null,
    autoSaveTimer: null,

    // Mobile & Tablet Responsive Drawer State
    mobileMenuOpen: false,
    isSubmittingUpgrade: false,

    get filteredAdminUsers() {
      if (!this.adminUserSearchQuery) return this.adminUsersList;
      const q = this.adminUserSearchQuery.toLowerCase();
      return this.adminUsersList.filter(u => 
        (u.email && u.email.toLowerCase().includes(q)) ||
        (u.full_name && u.full_name.toLowerCase().includes(q))
      );
    },

    toggleDarkMode() {
      this.darkMode = !this.darkMode;
      const html = document.documentElement;
      if (this.darkMode) {
        html.classList.remove('light-mode');
        html.style.backgroundColor = '#020617';
        html.style.color = '#f1f5f9';
      } else {
        html.classList.add('light-mode');
        html.style.backgroundColor = '#f1f5f9';
        html.style.color = '#0f172a';
      }
      localStorage.setItem('dreemfolio_theme', this.darkMode ? 'dark' : 'light');
      this.$nextTick(() => { if (window.lucide) window.lucide.createIcons(); });
    },

    async init() {
      // Check stored SaaS authentication token
      const token = localStorage.getItem('saas_token');
      if (token) {
        try {
          const authRes = await fetch('/api/auth/me', {
            headers: { 'Authorization': `Bearer ${token}` }
          });
          if (authRes.ok) {
            this.currentUser = await authRes.json();
          } else {
            localStorage.removeItem('saas_token');
            this.currentUser = null;
          }
        } catch (e) {
          console.warn('SaaS session restore error:', e);
        }
      }

      // Restore theme preference
      const savedTheme = localStorage.getItem('dreemfolio_theme');
      if (savedTheme === 'light') {
        this.darkMode = false;
        document.documentElement.classList.add('light-mode');
        document.documentElement.style.backgroundColor = '#f1f5f9';
        document.documentElement.style.color = '#0f172a';
      }

      // Fetch dynamic subscription plans from MySQL
      await this.loadDynamicPlans();

      // Initialize Google OAuth2 Identity Services
      await this.initGoogleAuth();

      // Load saved API key
      this.userApiKey = localStorage.getItem('dreemfolio_gemini_api_key') || '';

      // Watch showAuthModal to automatically render Google button when modal opens
      this.$watch('showAuthModal', (isOpen) => {
        if (isOpen) {
          this.renderGoogleButton();
        }
      });

      // Watch currentUser changes to refresh Lucide icons and reset avatar error
      this.$watch('currentUser', () => {
        this.avatarImgFailed = false;
        this.$nextTick(() => {
          if (window.lucide && typeof window.lucide.createIcons === 'function') {
            window.lucide.createIcons();
          }
          setTimeout(() => {
            if (window.lucide && typeof window.lucide.createIcons === 'function') {
              window.lucide.createIcons();
            }
          }, 60);
        });
      });

      // Initialize Lucide icons
      this.$nextTick(() => {
        if (window.lucide && typeof window.lucide.createIcons === 'function') {
          window.lucide.createIcons();
        }
        setTimeout(() => {
          if (window.lucide && typeof window.lucide.createIcons === 'function') {
            window.lucide.createIcons();
          }
        }, 100);
      });

      // Listen for direct resume download request from portfolio iframe
      window.addEventListener('message', (event) => {
        if (event.data === 'download_resume') {
          this.downloadResumePdf();
        }
      });

      // Fetch sample data
      try {
        const res = await fetch('/api/sample-data');
        if (res.ok) {
          this.sampleData = await res.json();
          if (this.sampleData.software_engineer) {
            this.sampleJD = this.sampleData.software_engineer.job_description;
          }
        }
      } catch (err) {
        console.warn('Could not fetch sample data:', err);
      }
    },

    openQuotaLimitModal(opts = {}) {
      this.quotaLimitData = {
        title: opts.title || 'Daily Free Limit Reached',
        message: opts.message || 'You have reached the daily free tier limit. Upgrade to Pro for unlimited access!',
        feature: opts.feature || '',
        requiredPlan: opts.requiredPlan || 'pro'
      };
      this.showQuotaLimitModal = true;
      this.$nextTick(() => { if (window.lucide) window.lucide.createIcons(); });
    },

    openLegalModal(tab = 'privacy') {
      this.activeLegalTab = tab;
      this.showLegalModal = true;
      this.$nextTick(() => {
        if (window.lucide && typeof window.lucide.createIcons === 'function') {
          window.lucide.createIcons();
        }
        setTimeout(() => {
          if (window.lucide && typeof window.lucide.createIcons === 'function') {
            window.lucide.createIcons();
          }
        }, 60);
      });
    },

    scrollToPreview() {
      const previewEl = document.getElementById('preview-pane') || document.querySelector('main');
      if (previewEl) {
        previewEl.scrollIntoView({ behavior: 'smooth' });
      }
    },

    async refreshCurrentUser() {
      const token = localStorage.getItem('saas_token');
      if (token) {
        try {
          const authRes = await fetch('/api/auth/me', {
            headers: { 'Authorization': `Bearer ${token}` }
          });
          if (authRes.ok) {
            this.currentUser = await authRes.json();
            this.$nextTick(() => { if (window.lucide) window.lucide.createIcons(); });
          }
        } catch (e) {
          console.warn('SaaS user profile refresh error:', e);
        }
      }
    },

    saveApiKey() {
      localStorage.setItem('dreemfolio_gemini_api_key', this.userApiKey);
      this.showApiModal = false;
      alert('Gemini API Key saved successfully!');
    },

    loadSample(type) {
      const sample = this.sampleData[type];
      if (sample) {
        this.resumeText = sample.raw_text;
        this.jobDescription = sample.job_description;
        this.targetJobTitle = sample.title || '';
        this.fileName = `${sample.name.replace(/\s+/g, '_')}_Resume_Sample.pdf`;
        this.extractedCandidateName = sample.name;
        this.showRawText = true;
        
        this.$nextTick(() => {
          if (window.lucide) window.lucide.createIcons();
        });
      }
    },

    clearFile() {
      this.fileName = '';
      this.resumeText = '';
      this.extractedCandidateName = '';
    },

    async handleFileUpload(event) {
      const file = event.target.files[0];
      if (file) {
        await this.uploadFile(file);
      }
    },

    async handleFileDrop(event) {
      this.dragOver = false;
      const file = event.dataTransfer.files[0];
      if (file) {
        await this.uploadFile(file);
      }
    },

    async uploadFile(file) {
      this.isUploading = true;
      this.fileName = file.name;

      const formData = new FormData();
      formData.append('file', file);

      try {
        const res = await fetch('/api/upload', {
          method: 'POST',
          body: formData,
        });

        if (!res.ok) {
          const errData = await res.json();
          throw new Error(errData.detail || 'Failed to parse resume');
        }

        const data = await res.json();
        this.resumeText = data.text;
        this.extractedCandidateName = data.extracted_name || '';
        this.showRawText = true;
      } catch (err) {
        alert('Upload Error: ' + err.message);
        this.fileName = '';
      } finally {
        this.isUploading = false;
        this.$nextTick(() => {
          if (window.lucide) window.lucide.createIcons();
        });
      }
    },

    async tailorResume() {
      // 1. Gated check: Login or register required to generate
      if (!this.currentUser) {
        this.pendingAction = 'tailor';
        this.openAuthModal('register', '🔒 Free Account Required: Sign in or register in seconds to generate your AI-optimized resume, access all visual formats, and download PDFs!');
        return;
      }

      if (!this.resumeText || !this.jobDescription) {
        alert('Please provide both your existing resume text and the target job description.');
        return;
      }

      this.isTailoring = true;
      this.tailorStatusText = 'Extracting candidate background & target keywords...';

      const statusSteps = [
        'Extracting candidate background & target keywords...',
        'Synthesizing quantifiable achievement metrics...',
        'Rewriting experience bullets with active verbs...',
        'Generating 100% ATS single-column & Visual Designer PDFs...',
        'Designing responsive Personal Portfolio Website...',
        'Drafting tailored 3-paragraph cover letter...'
      ];
      let stepIdx = 0;
      const statusInterval = setInterval(() => {
        stepIdx = (stepIdx + 1) % statusSteps.length;
        this.tailorStatusText = statusSteps[stepIdx];
      }, 1500);

      try {
        const payload = {
          resume_text: this.resumeText,
          job_description: this.jobDescription,
          job_title: this.targetJobTitle || null,
          company_name: this.targetCompany || null,
          role_archetype: this.roleArchetype || 'auto',
          template_style: this.currentTemplate,
          cover_letter_tone: this.coverLetterTone,
          api_key: this.userApiKey || null,
        };

        const token = localStorage.getItem('saas_token');
        const headers = { 'Content-Type': 'application/json' };
        if (token) headers['Authorization'] = `Bearer ${token}`;

        const res = await fetch('/api/tailor', {
          method: 'POST',
          headers: headers,
          body: JSON.stringify(payload),
        });

        if (!res.ok) {
          const errData = await res.json();
          if (res.status === 402) {
            this.showPricingModal = true;
            const quotaMsg = typeof errData.detail === 'object' ? errData.detail.message : errData.detail;
            throw new Error(quotaMsg || 'Daily free AI quota reached (2/2 runs). Upgrade to Pro ($9/mo) or Elite ($19/mo) for unlimited AI tailoring!');
          }
          throw new Error(typeof errData.detail === 'object' ? JSON.stringify(errData.detail) : (errData.detail || 'Failed to tailor resume'));
        }

        this.tailoredData = await res.json();
        this.currentTemplate = this.tailoredData.template_style || 'classic';
        if (this.tailoredData.role_archetype) {
          this.roleArchetype = this.tailoredData.role_archetype;
        }

        // Initialize safe default customization properties
        if (!this.tailoredData.personal_info.social_links) {
          this.tailoredData.personal_info.social_links = [];
        }
        if (!this.tailoredData.certifications) {
          this.tailoredData.certifications = [];
        }
        if (!this.tailoredData.projects) {
          this.tailoredData.projects = [];
        }
        if (!this.tailoredData.education) {
          this.tailoredData.education = [];
        }
        if (!this.tailoredData.skill_categories) {
          this.tailoredData.skill_categories = [];
        }

        // Section visibility defaults
        this.tailoredData.show_photo = this.tailoredData.show_photo ?? Boolean(this.tailoredData.personal_info?.avatar_url);
        this.tailoredData.show_summary = this.tailoredData.show_summary ?? true;
        this.tailoredData.show_skills = this.tailoredData.show_skills ?? true;
        this.tailoredData.show_experience = this.tailoredData.show_experience ?? true;
        this.tailoredData.show_projects = this.tailoredData.show_projects ?? true;
        this.tailoredData.show_education = this.tailoredData.show_education ?? true;
        this.tailoredData.show_certifications = this.tailoredData.show_certifications ?? true;
        this.tailoredData.font_size_scale = this.tailoredData.font_size_scale || 'standard';
        this.tailoredData.font_family = this.tailoredData.font_family || 'Helvetica';
        this.tailoredData.show_skill_bars = this.tailoredData.show_skill_bars ?? true;
        this.tailoredData.skill_bar_style = this.tailoredData.skill_bar_style || 'segmented';
        this.tailoredData.section_order = this.tailoredData.section_order || ['summary', 'skills', 'experience', 'projects', 'education', 'certifications'];

        // Cover Letter defaults
        if (!this.tailoredData.cover_letter) {
          this.tailoredData.cover_letter = {};
        }
        const cl = this.tailoredData.cover_letter;
        cl.layout_style = cl.layout_style || 'modern_banner';
        cl.signature_mode = cl.signature_mode || 'script';
        cl.letter_date = cl.letter_date || new Date().toLocaleDateString('en-US', { year: 'numeric', month: 'long', day: 'numeric' });
        cl.sign_off_title = cl.sign_off_title || this.tailoredData.target_job_title || 'Software Engineer';

        // Portfolio Customization defaults
        this.tailoredData.portfolio_theme = this.tailoredData.portfolio_theme || 'bento_grid';
        this.tailoredData.portfolio_accent_color = this.tailoredData.portfolio_accent_color || '#6366f1';
        this.tailoredData.portfolio_font = this.tailoredData.portfolio_font || 'Inter';
        this.tailoredData.portfolio_show_bio = this.tailoredData.portfolio_show_bio ?? true;
        this.tailoredData.portfolio_show_skills = this.tailoredData.portfolio_show_skills ?? true;
        this.tailoredData.portfolio_show_experience = this.tailoredData.portfolio_show_experience ?? true;
        this.tailoredData.portfolio_show_projects = this.tailoredData.portfolio_show_projects ?? true;
        // Sync direct fields into social_links if not already present
        const pInfo = this.tailoredData.personal_info;
        const existingNames = new Set((pInfo.social_links || []).map(l => (l.name || '').toLowerCase()));
        if (pInfo.linkedin && !Array.from(existingNames).some(n => n.includes('linkedin'))) {
          pInfo.social_links.push({ name: 'LinkedIn', url: pInfo.linkedin, icon: 'linkedin', enabled: true });
        }
        if (pInfo.github && !Array.from(existingNames).some(n => n.includes('github'))) {
          pInfo.social_links.push({ name: 'GitHub', url: pInfo.github, icon: 'github', enabled: true });
        }
        if (pInfo.portfolio && !Array.from(existingNames).some(n => n.includes('portfolio') || n.includes('website'))) {
          pInfo.social_links.push({ name: 'Portfolio', url: pInfo.portfolio, icon: 'globe', enabled: true });
        }

        // Always calculate dynamic portfolio metrics 100% strictly matched with the latest generated CV data
        const projCount = (this.tailoredData.projects && this.tailoredData.projects.length) || 0;
        const expCount = (this.tailoredData.work_experience && this.tailoredData.work_experience.length) || 1;
        const totalSkills = (this.tailoredData.skill_categories || []).reduce((acc, c) => acc + ((c.skills && c.skills.length) || 0), 0);
        const certCount = (this.tailoredData.certifications && this.tailoredData.certifications.length) || 0;

        this.tailoredData.portfolio_metrics = [
          { label: 'Key Projects', value: projCount > 0 ? `${projCount}+` : 'Verified' },
          { label: 'Experience', value: `${expCount}+ Roles` },
          { label: 'Technical Stack', value: totalSkills > 0 ? `${totalSkills}+ Skills` : 'Full Stack' },
          { label: certCount > 0 ? 'Certifications' : 'ATS Compatibility', value: certCount > 0 ? `${certCount}+ Certs` : '99.8%' }
        ];

        this.portfolioTheme = this.tailoredData.portfolio_theme;
        this.portfolioAccent = this.tailoredData.portfolio_accent_color;
        this.portfolioFont = this.tailoredData.portfolio_font;

        // Render both PDF and Portfolio
        await this.renderPdfPreview();
        await this.renderPortfolioPreview();

        // Automatically save newly tailored resume into MySQL!
        this.currentResumeId = null;
        await this.performAutoSave();

        // Auto-sync Live Job Hunter with authentic role & location
        if (this.tailoredData.target_job_title) {
          this.jobSearchQuery.keywords = this.tailoredData.target_job_title;
        }
        if (this.tailoredData.personal_info?.location && !this.tailoredData.personal_info.location.toLowerCase().includes('available for')) {
          this.jobSearchQuery.location = this.tailoredData.personal_info.location;
        }
        // If physical trade or medical, ensure default mode is On-site
        if (this.tailoredData.role_archetype === 'trade_technical' || this.tailoredData.role_archetype === 'healthcare_medical') {
          this.jobSearchQuery.work_mode = 'onsite';
        } else {
          this.jobSearchQuery.work_mode = 'all';
        }
        // Reset cached hunter search results so new tab visit pulls fresh authentic data
        this.jobSearchResults = [];

        // Refresh user quotas after AI run
        await this.refreshCurrentUser();

      } catch (err) {
        if (err.message && (err.message.toLowerCase().includes('quota') || err.message.includes('Daily free AI generation limit'))) {
          this.openQuotaLimitModal({
            title: 'Daily AI Generation Limit Reached',
            message: err.message,
            requiredPlan: 'pro'
          });
        } else {
          alert('Optimization Error: ' + err.message);
        }
      } finally {
        clearInterval(statusInterval);
        this.isTailoring = false;
        this.$nextTick(() => {
          if (window.lucide) window.lucide.createIcons();
        });
      }
    },

    async setTemplate(templateName) {
      this.currentTemplate = templateName;
      // Always switch to resume tab so preview is visible
      this.activeTab = 'resume';
      if (this.tailoredData) {
        this.tailoredData.template_style = templateName;
        // Null out first so Alpine re-mounts the iframe cleanly
        this.pdfBlobUrl = null;
        await this.renderPdfPreview();
      }
    },

    async setPortfolioTheme(themeName) {
      this.portfolioTheme = themeName;
      if (this.tailoredData) {
        this.tailoredData.portfolio_theme = themeName;
      }
      this.activeTab = 'portfolio';
      await this.renderPortfolioPreview();
      this.triggerAutoSave();
    },

    setPortfolioAccent(colorHex) {
      this.portfolioAccent = colorHex;
      if (this.tailoredData) {
        this.tailoredData.portfolio_accent_color = colorHex;
      }
      this.renderPortfolioPreview();
      this.triggerAutoSave();
    },

    updatePortfolioAccent(colorHex) {
      this.portfolioAccent = colorHex;
      if (this.tailoredData) {
        this.tailoredData.portfolio_accent_color = colorHex;
      }
      this.refreshAllPreviews();
    },

    updatePortfolioFont(fontName) {
      this.portfolioFont = fontName;
      if (this.tailoredData) {
        this.tailoredData.portfolio_font = fontName;
      }
      this.refreshAllPreviews();
    },

    // ─────────────────────────────────────────────────────────────────────────
    // 100% FULL PORTFOLIO CRUD OPERATIONS
    // ─────────────────────────────────────────────────────────────────────────
    addPortfolioMetric() {
      if (!this.tailoredData) return;
      if (!this.tailoredData.portfolio_metrics) this.tailoredData.portfolio_metrics = [];
      this.tailoredData.portfolio_metrics.push({ label: 'Key Achievement', value: '10+' });
      this.refreshAllPreviews();
      this.$nextTick(() => { if (window.lucide) window.lucide.createIcons(); });
    },

    removePortfolioMetric(idx) {
      if (!this.tailoredData || !this.tailoredData.portfolio_metrics) return;
      this.tailoredData.portfolio_metrics.splice(idx, 1);
      this.refreshAllPreviews();
    },

    addPortfolioProject() {
      if (!this.tailoredData) return;
      if (!this.tailoredData.projects) this.tailoredData.projects = [];
      this.tailoredData.projects.unshift({
        name: 'New Featured Project',
        technologies: ['TypeScript', 'React', 'FastAPI'],
        link: 'https://github.com/example/project',
        demo_url: 'https://example.com/demo',
        description_bullets: ['Architected scalable full-stack system with high performance and measurable impact.']
      });
      this.refreshAllPreviews();
      this.$nextTick(() => { if (window.lucide) window.lucide.createIcons(); });
    },

    removePortfolioProject(idx) {
      if (!this.tailoredData || !this.tailoredData.projects) return;
      if (confirm('Are you sure you want to remove this project?')) {
        this.tailoredData.projects.splice(idx, 1);
        this.refreshAllPreviews();
      }
    },

    addProjectBullet(pIdx) {
      if (!this.tailoredData || !this.tailoredData.projects[pIdx]) return;
      if (!this.tailoredData.projects[pIdx].description_bullets) {
        this.tailoredData.projects[pIdx].description_bullets = [];
      }
      this.tailoredData.projects[pIdx].description_bullets.push('Engineered mission-critical service optimizing performance by 35%.');
      this.refreshAllPreviews();
    },

    removeProjectBullet(pIdx, bIdx) {
      if (!this.tailoredData || !this.tailoredData.projects[pIdx]) return;
      this.tailoredData.projects[pIdx].description_bullets.splice(bIdx, 1);
      this.refreshAllPreviews();
    },

    addPortfolioSkill(catIdx) {
      if (!this.tailoredData || !this.tailoredData.skill_categories[catIdx]) return;
      const skillName = prompt('Enter new skill name:');
      if (skillName && skillName.trim()) {
        const cat = this.tailoredData.skill_categories[catIdx];
        cat.skills.push(skillName.trim());
        if (!cat.skill_levels) cat.skill_levels = {};
        cat.skill_levels[skillName.trim()] = 90;
        this.refreshAllPreviews();
      }
    },

    removePortfolioSkill(catIdx, sIdx) {
      if (!this.tailoredData || !this.tailoredData.skill_categories[catIdx]) return;
      this.tailoredData.skill_categories[catIdx].skills.splice(sIdx, 1);
      this.refreshAllPreviews();
    },

    updateSkillLevel(catIdx, skillName, level) {
      if (!this.tailoredData || !this.tailoredData.skill_categories[catIdx]) return;
      const cat = this.tailoredData.skill_categories[catIdx];
      if (!cat.skill_levels) cat.skill_levels = {};
      cat.skill_levels[skillName] = parseInt(level, 10) || 80;
      this.refreshAllPreviews();
    },

    addPortfolioExperience() {
      if (!this.tailoredData) return;
      if (!this.tailoredData.work_experience) this.tailoredData.work_experience = [];
      this.tailoredData.work_experience.unshift({
        job_title: 'Senior Software Engineer',
        company: 'Innovate Tech Labs',
        location: 'Remote',
        start_date: '2024',
        end_date: 'Present',
        bullet_points: ['Spearheaded enterprise architecture development delivering reliable cloud solutions.']
      });
      this.refreshAllPreviews();
      this.$nextTick(() => { if (window.lucide) window.lucide.createIcons(); });
    },

    removePortfolioExperience(idx) {
      if (!this.tailoredData || !this.tailoredData.work_experience) return;
      if (confirm('Are you sure you want to remove this career milestone?')) {
        this.tailoredData.work_experience.splice(idx, 1);
        this.refreshAllPreviews();
      }
    },

    async renderPdfPreview() {
      if (!this.tailoredData) return;

      try {
        // Stamp current template into payload before every call
        this.tailoredData.template_style = this.currentTemplate;

        const endpoint = this.activeTab === 'cover_letter'
          ? '/api/generate-pdf/cover-letter'
          : '/api/generate-pdf/resume';

        const res = await fetch(endpoint, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(this.tailoredData),
        });

        if (!res.ok) {
          const errText = await res.text();
          throw new Error('PDF Generation failed: ' + errText);
        }

        const blob = await res.blob();
        if (this.pdfBlobUrl) {
          URL.revokeObjectURL(this.pdfBlobUrl);
        }
        this.pdfBlobUrl = URL.createObjectURL(blob) + '#toolbar=0&navpanes=0';
        this.pdfBlobKey = Date.now();
      } catch (err) {
        console.error('PDF Preview render error:', err);
      }
    },

    async renderPortfolioPreview() {
      if (!this.tailoredData) return;

      try {
        const res = await fetch(`/api/generate-portfolio?theme=${this.portfolioTheme}`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(this.tailoredData),
        });

        if (!res.ok) throw new Error('Portfolio generation failed');

        const data = await res.json();
        this.portfolioHtml = data.html;
      } catch (err) {
        console.error('Portfolio Preview render error:', err);
      }
    },

    syncSocialLinksToDirectFields() {
      if (!this.tailoredData || !this.tailoredData.personal_info) return;
      const info = this.tailoredData.personal_info;
      if (!info.social_links) {
        info.social_links = [];
        return;
      }

      let activeLinkedin = '';
      let activeGithub = '';
      let activePortfolio = '';

      for (const link of info.social_links) {
        if (!link.enabled || !link.url || !link.url.trim()) continue;
        const name = (link.name || '').toLowerCase().trim();
        const url = link.url.trim();

        if (name.includes('linkedin')) {
          if (!activeLinkedin) activeLinkedin = url;
        } else if (name.includes('github')) {
          if (!activeGithub) activeGithub = url;
        } else if (name.includes('portfolio') || name.includes('website') || name.includes('blog') || name.includes('site')) {
          if (!activePortfolio) activePortfolio = url;
        }
      }

      // Explicitly overwrite so turning OFF immediately clears them!
      info.linkedin = activeLinkedin;
      info.github = activeGithub;
      info.portfolio = activePortfolio;
    },

    toggleSocialLink(link) {
      if (!link) return;
      link.enabled = !link.enabled;
      this.syncSocialLinksToDirectFields();
      this.renderPdfPreview();
      this.renderPortfolioPreview();
      this.triggerAutoSave();
    },

    refreshAllPreviews() {
      this.syncSocialLinksToDirectFields();

      clearTimeout(this.debounceTimer);
      this.debounceTimer = setTimeout(() => {
        this.renderPdfPreview();
        this.renderPortfolioPreview();
      }, 300);

      // Trigger automatic save to MySQL whenever any change occurs!
      this.triggerAutoSave();
    },

    triggerAutoSave() {
      if (!this.currentUser || !this.tailoredData) return;
      this.autoSaveStatus = 'unsaved';

      if (this.autoSaveTimer) {
        clearTimeout(this.autoSaveTimer);
      }

      this.autoSaveTimer = setTimeout(async () => {
        await this.performAutoSave();
      }, 1200); // 1.2s debounced auto-save after editing stops
    },

    async performAutoSave() {
      if (!this.currentUser || !this.tailoredData) return;
      if (!this.currentUser.plan_tier || this.currentUser.plan_tier === 'free') {
        this.autoSaveStatus = 'free_disabled';
        return;
      }
      this.autoSaveStatus = 'saving';

      const token = localStorage.getItem('saas_token');
      if (!token) {
        this.autoSaveStatus = 'saved';
        return;
      }

      try {
        const title = `${this.tailoredData.target_job_title || 'Resume'} - ${this.tailoredData.target_company || 'MySQL Auto-Save'}`;
        const res = await fetch('/api/user/resumes', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${token}`
          },
          body: JSON.stringify({
            resume_id: this.currentResumeId,
            title: title,
            resume_data: this.tailoredData
          })
        });

        if (res.ok) {
          const data = await res.json();
          this.currentResumeId = data.resume_id;
          this.autoSaveStatus = 'saved';
          this.lastSavedTime = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });
        } else {
          this.autoSaveStatus = 'error';
        }
      } catch (err) {
        console.warn('MySQL Auto-save network error:', err);
        this.autoSaveStatus = 'error';
      }
    },

    // ── FULL CUSTOMIZATION HELPERS ───────────────────────────────────────

    handlePhotoUpload(event) {
      const file = event.target.files[0];
      if (!file) return;
      if (!file.type.startsWith('image/')) {
        alert('Please select a valid image file (PNG, JPG, JPEG, WEBP).');
        return;
      }
      const reader = new FileReader();
      reader.onload = (e) => {
        if (this.tailoredData) {
          this.tailoredData.personal_info.avatar_url = e.target.result;
          this.tailoredData.show_photo = true;
          this.refreshAllPreviews();
        }
      };
      reader.readAsDataURL(file);
    },

    // Design & Styling
    setAccentColor(colorHex) {
      if (!this.tailoredData) return;
      this.tailoredData.custom_accent_color = colorHex;
      this.refreshAllPreviews();
    },

    setFontFamily(family) {
      if (!this.tailoredData) return;
      this.tailoredData.font_family = family;
      this.refreshAllPreviews();
    },

    setFontScale(scale) {
      if (!this.tailoredData) return;
      this.tailoredData.font_size_scale = scale;
      this.refreshAllPreviews();
    },

    toggleSection(key) {
      if (!this.tailoredData) return;
      this.tailoredData[key] = !this.tailoredData[key];
      this.refreshAllPreviews();
    },

    // Role Blueprint Manager
    getRoleArchetypeName(arch) {
      const map = {
        'software_engineering': 'Software & Tech',
        'trade_technical': 'Trades & Automotive',
        'management_executive': 'Management & PM',
        'healthcare_medical': 'Healthcare & Clinical',
        'general_professional': 'Universal Standard'
      };
      return map[arch] || 'Auto-Detect';
    },

    // Section Order & Positions Manager
    getSectionDisplayName(secKey) {
      const names = {
        summary: 'Professional Summary / Objective',
        skills: 'Technical Skills & Competencies',
        experience: 'Work Experience',
        projects: 'Key Projects & Systems',
        education: 'Education & Qualifications',
        certifications: 'Certifications & Awards'
      };
      return names[secKey] || secKey;
    },

    moveSection(idx, direction) {
      if (!this.tailoredData) return;
      if (!this.tailoredData.section_order) {
        this.tailoredData.section_order = ['summary', 'skills', 'experience', 'projects', 'education', 'certifications'];
      }
      const targetIdx = idx + direction;
      if (targetIdx < 0 || targetIdx >= this.tailoredData.section_order.length) return;
      const item = this.tailoredData.section_order.splice(idx, 1)[0];
      this.tailoredData.section_order.splice(targetIdx, 0, item);
      this.refreshAllPreviews();
      this.$nextTick(() => { if (window.lucide) window.lucide.createIcons(); });
    },

    resetSectionOrder() {
      if (!this.tailoredData) return;
      this.tailoredData.section_order = ['summary', 'skills', 'experience', 'projects', 'education', 'certifications'];
      this.refreshAllPreviews();
      this.$nextTick(() => { if (window.lucide) window.lucide.createIcons(); });
    },

    // Technical Skills Customizer
    addSkillCategory() {
      if (!this.tailoredData) return;
      if (!this.tailoredData.skill_categories) {
        this.tailoredData.skill_categories = [];
      }
      this.tailoredData.skill_categories.push({
        category_name: 'New Skill Category',
        skills: ['Skill A', 'Skill B']
      });
      this.refreshAllPreviews();
      this.$nextTick(() => { if (window.lucide) window.lucide.createIcons(); });
    },

    removeSkillCategory(catIdx) {
      if (!this.tailoredData || !this.tailoredData.skill_categories) return;
      this.tailoredData.skill_categories.splice(catIdx, 1);
      this.refreshAllPreviews();
    },

    addSkillTag(catIdx) {
      if (!this.tailoredData || !this.tailoredData.skill_categories[catIdx]) return;
      const inputVal = (this.newSkillInputs[catIdx] || '').trim();
      const skillName = inputVal || 'New Skill';
      this.tailoredData.skill_categories[catIdx].skills.push(skillName);
      if (!this.tailoredData.skill_categories[catIdx].skill_levels) {
        this.tailoredData.skill_categories[catIdx].skill_levels = {};
      }
      this.tailoredData.skill_categories[catIdx].skill_levels[skillName] = 85;
      this.newSkillInputs[catIdx] = '';
      this.refreshAllPreviews();
    },

    removeSkillTag(catIdx, sIdx) {
      if (!this.tailoredData || !this.tailoredData.skill_categories[catIdx]) return;
      const removed = this.tailoredData.skill_categories[catIdx].skills.splice(sIdx, 1);
      if (removed && removed[0] && this.tailoredData.skill_categories[catIdx].skill_levels) {
        delete this.tailoredData.skill_categories[catIdx].skill_levels[removed[0]];
      }
      this.refreshAllPreviews();
    },

    updateSkillLevel(cat, skillName, value) {
      if (!cat.skill_levels) cat.skill_levels = {};
      const num = Math.max(10, Math.min(100, parseInt(value, 10) || 85));
      cat.skill_levels[skillName] = num;
      this.refreshAllPreviews();
    },

    setSkillBarStyle(style) {
      if (!this.tailoredData) return;
      this.tailoredData.skill_bar_style = style;
      this.refreshAllPreviews();
    },

    // Work Experience Customizer
    addWorkExperience() {
      if (!this.tailoredData) return;
      if (!this.tailoredData.work_experience) this.tailoredData.work_experience = [];
      this.tailoredData.work_experience.unshift({
        job_title: 'Senior Software Engineer',
        company: 'Company Name',
        location: 'Remote',
        start_date: '2023',
        end_date: 'Present',
        bullet_points: [
          'Architected and deployed high-performance software systems improving scalability by 35%.',
          'Collaborated with cross-functional teams to streamline CI/CD delivery pipelines.'
        ]
      });
      this.refreshAllPreviews();
      this.$nextTick(() => { if (window.lucide) window.lucide.createIcons(); });
    },

    removeWorkExperience(index) {
      if (!this.tailoredData || !this.tailoredData.work_experience) return;
      this.tailoredData.work_experience.splice(index, 1);
      this.refreshAllPreviews();
    },

    addBullet(expIdx) {
      if (!this.tailoredData || !this.tailoredData.work_experience[expIdx]) return;
      this.tailoredData.work_experience[expIdx].bullet_points.push(
        'Implemented key software modules, improving system reliability and performance turnaround.'
      );
      this.refreshAllPreviews();
    },

    removeBullet(expIdx, bIdx) {
      if (!this.tailoredData || !this.tailoredData.work_experience[expIdx]) return;
      this.tailoredData.work_experience[expIdx].bullet_points.splice(bIdx, 1);
      this.refreshAllPreviews();
    },

    // Key Projects Customizer
    addProject() {
      if (!this.tailoredData) return;
      if (!this.tailoredData.projects) this.tailoredData.projects = [];
      this.tailoredData.projects.unshift({
        name: 'Full-Stack Web App',
        technologies: ['TypeScript', 'React', 'Node.js', 'PostgreSQL'],
        link: 'https://github.com/...',
        demo_url: 'https://demo.app',
        description_bullets: [
          'Engineered modern scalable cloud application with 99.9% availability.',
          'Integrated secure RESTful APIs and real-time event subscriptions.'
        ]
      });
      this.refreshAllPreviews();
      this.$nextTick(() => { if (window.lucide) window.lucide.createIcons(); });
    },

    removeProject(pIdx) {
      if (!this.tailoredData || !this.tailoredData.projects) return;
      this.tailoredData.projects.splice(pIdx, 1);
      this.refreshAllPreviews();
    },

    addProjectBullet(pIdx) {
      if (!this.tailoredData || !this.tailoredData.projects[pIdx]) return;
      this.tailoredData.projects[pIdx].description_bullets.push(
        'Engineered modular backend services cutting latency by 25%.'
      );
      this.refreshAllPreviews();
    },

    removeProjectBullet(pIdx, bIdx) {
      if (!this.tailoredData || !this.tailoredData.projects[pIdx]) return;
      this.tailoredData.projects[pIdx].description_bullets.splice(bIdx, 1);
      this.refreshAllPreviews();
    },

    // Education Customizer
    addEducation() {
      if (!this.tailoredData) return;
      if (!this.tailoredData.education) this.tailoredData.education = [];
      this.tailoredData.education.unshift({
        degree: 'BSc in Software Engineering',
        institution: 'University / Institute Name',
        location: 'Remote',
        graduation_year: '2021 - 2025',
        details: 'First Class Honours'
      });
      this.refreshAllPreviews();
      this.$nextTick(() => { if (window.lucide) window.lucide.createIcons(); });
    },

    removeEducation(eduIdx) {
      if (!this.tailoredData || !this.tailoredData.education) return;
      this.tailoredData.education.splice(eduIdx, 1);
      this.refreshAllPreviews();
    },

    // Certifications Customizer
    addCertification() {
      if (!this.tailoredData) return;
      if (!this.tailoredData.certifications) this.tailoredData.certifications = [];
      this.tailoredData.certifications.push({
        name: 'AWS Certified Solutions Architect',
        issuer: 'Amazon Web Services',
        year: '2024'
      });
      this.refreshAllPreviews();
      this.$nextTick(() => { if (window.lucide) window.lucide.createIcons(); });
    },

    removeCertification(certIdx) {
      if (!this.tailoredData || !this.tailoredData.certifications) return;
      this.tailoredData.certifications.splice(certIdx, 1);
      this.refreshAllPreviews();
    },

    // Social Links Manager
    addSocialLink() {
      if (!this.tailoredData) return;
      if (!this.tailoredData.personal_info.social_links) {
        this.tailoredData.personal_info.social_links = [];
      }
      this.tailoredData.personal_info.social_links.push({
        name: 'Website',
        url: 'https://',
        icon: 'globe',
        enabled: true
      });
      this.syncSocialLinksToDirectFields();
      this.renderPdfPreview();
      this.renderPortfolioPreview();
      this.triggerAutoSave();
      this.$nextTick(() => { if (window.lucide) window.lucide.createIcons(); });
    },

    removeSocialLink(index) {
      if (!this.tailoredData || !this.tailoredData.personal_info.social_links) return;
      this.tailoredData.personal_info.social_links.splice(index, 1);
      this.syncSocialLinksToDirectFields();
      this.renderPdfPreview();
      this.renderPortfolioPreview();
      this.triggerAutoSave();
    },

    // Custom Domain Manager
    async verifyDomain() {
      if (!this.customDomainInput.trim()) {
        alert('Please enter your domain name (e.g. malitha.dev)');
        return;
      }
      const slug = (this.tailoredData?.personal_info.full_name || 'developer').toLowerCase().replace(/\s+/g, '-');
      const token = localStorage.getItem('saas_token');
      try {
        const res = await fetch('/api/domain/verify', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            ...(token ? { 'Authorization': `Bearer ${token}` } : {})
          },
          body: JSON.stringify({ domain: this.customDomainInput, slug: slug })
        });

        if (!res.ok) {
          const errData = await res.json();
          if (res.status === 403) {
            this.showDomainModal = false;
            this.showPricingModal = true;
            const msg = typeof errData.detail === 'object' ? errData.detail.message : errData.detail;
            throw new Error(msg || 'Custom private domains require the Executive Elite plan. Please upgrade to unlock.');
          }
          if (res.status === 401) {
            this.showDomainModal = false;
            this.openAuthModal('login');
            throw new Error('Please log in to connect a custom private domain.');
          }
          throw new Error(typeof errData.detail === 'object' ? JSON.stringify(errData.detail) : (errData.detail || 'Domain verification failed'));
        }

        const data = await res.json();
        if (this.tailoredData) {
          this.tailoredData.personal_info.custom_domain = data.domain;
          this.refreshAllPreviews();
        }
        alert(`✅ Domain "${data.domain}" verified!\nPoint your CNAME record to: cname.dreemfolio.com`);
        this.showDomainModal = false;
      } catch (err) {
        alert('Domain Error: ' + err.message);
      }
    },

    async verifyAndConnectDomain() {
      if (!this.tailoredData?.personal_info.custom_domain) {
        alert('Please enter your custom domain name');
        return;
      }
      this.customDomainInput = this.tailoredData.personal_info.custom_domain;
      await this.verifyDomain();
    },

    async publishLivePortfolio() {
      if (!this.tailoredData) return;

      if (!this.currentUser) {
        this.openAuthModal('register', '🔒 Free Account Required: Sign in or register to publish your portfolio live to the web!');
        return;
      }

      const isFree = !this.currentUser.plan_tier || this.currentUser.plan_tier === 'free';
      if (isFree) {
        this.openQuotaLimitModal({
          title: 'Live Web Portfolio Locked',
          message: 'Publishing your portfolio live to a public web URL (.dreemfolio.com) requires the Pro Career plan ($9/mo). Free users can customize, preview, and test all 8 portfolio themes on-screen! Upgrade to Pro to publish your live website.',
          requiredPlan: 'pro'
        });
        return;
      }

      this.isPublishing = true;

      try {
        const token = localStorage.getItem('saas_token');
        const headers = { 'Content-Type': 'application/json' };
        if (token) headers['Authorization'] = `Bearer ${token}`;

        const res = await fetch(`/api/publish-portfolio?theme=${this.portfolioTheme}`, {
          method: 'POST',
          headers: headers,
          body: JSON.stringify(this.tailoredData),
        });

        if (!res.ok) {
          const errData = await res.json().catch(() => null);
          const msg = (errData && errData.detail && errData.detail.message) || (errData && errData.detail) || 'Failed to publish portfolio';
          if (res.status === 403) {
            this.openQuotaLimitModal({
              title: 'Live Web Portfolio Locked',
              message: msg,
              requiredPlan: 'pro'
            });
            return;
          }
          throw new Error(msg);
        }

        const data = await res.json();
        this.publishedLiveUrl = data.live_url;
        alert(`🎉 Awesome! Your portfolio is now published live at:\n${window.location.origin}${data.live_url}`);
      } catch (err) {
        alert('Publish Error: ' + err.message);
      } finally {
        this.isPublishing = false;
      }
    },

    async downloadPortfolioHtml() {
      if (!this.tailoredData) return;

      try {
        const res = await fetch(`/api/download-portfolio?theme=${this.portfolioTheme}`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(this.tailoredData),
        });

        if (!res.ok) throw new Error('Portfolio download failed');

        const blob = await res.blob();
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        const name = (this.tailoredData.personal_info.full_name || 'candidate').replace(/\s+/g, '_').toLowerCase();
        a.href = url;
        a.download = `${name}_portfolio.html`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
      } catch (err) {
        alert('Download Error: ' + err.message);
      }
    },

    async downloadResumePdf() {
      if (!this.currentUser) {
        this.openAuthModal('register', '🔒 Free Account Required: Sign in or register to download high-resolution ATS & Designer PDF resumes!');
        return;
      }
      if (!this.tailoredData) return;

      // Lifetime Quota checks for Free Tier
      const isVisual = ['visual_sidebar', 'creative_gradient', 'tech_noir', 'indigo_banner', 'emerald_prestige'].includes(this.currentTemplate);
      const isFree = !this.currentUser.plan_tier || this.currentUser.plan_tier === 'free';

      if (isFree) {
        if (isVisual && this.currentUser.remaining_visual_downloads !== undefined && this.currentUser.remaining_visual_downloads <= 0) {
          this.openQuotaLimitModal({
            title: 'Visual Photo CV Limit Reached',
            message: 'Your 1 free lifetime Visual Photo CV download has been used.\n\nUpgrade to Pro Career for unlimited high-resolution Visual and ATS downloads!',
            requiredPlan: 'pro'
          });
          return;
        }
        if (!isVisual && this.currentUser.remaining_ats_downloads !== undefined && this.currentUser.remaining_ats_downloads <= 0) {
          this.openQuotaLimitModal({
            title: 'Classic ATS Resume Limit Reached',
            message: 'Your 2 free lifetime Classic ATS downloads have been used.\n\nUpgrade to Pro Career for unlimited downloads in all formats!',
            requiredPlan: 'pro'
          });
          return;
        }
      }

      this.isDownloading = true;

      try {
        // Stamp template before sending
        this.tailoredData.template_style = this.currentTemplate;

        const token = localStorage.getItem('saas_token');
        const headers = { 'Content-Type': 'application/json' };
        if (token) headers['Authorization'] = `Bearer ${token}`;

        const res = await fetch('/api/generate-pdf/resume?download=true', {
          method: 'POST',
          headers: headers,
          body: JSON.stringify(this.tailoredData),
        });

        if (!res.ok) {
          const errData = await res.json().catch(() => null);
          const errCode = (errData && errData.detail && errData.detail.error_code) || '';
          const msg = (errData && errData.detail && errData.detail.message) || (errData && errData.detail) || 'PDF download failed';
          if (res.status === 403 || res.status === 402) {
            const title = errCode === 'visual_quota_exceeded'
              ? 'Visual Photo CV Limit Reached'
              : 'Classic ATS Resume Limit Reached';
            this.openQuotaLimitModal({
              title: title,
              message: msg,
              requiredPlan: 'pro'
            });
            return;
          }
          throw new Error(msg);
        }

        const blob = await res.blob();
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        const name = (this.tailoredData.personal_info.full_name || 'Resume').replace(/\s+/g, '_');
        const suffix = isVisual ? `Visual_${this.currentTemplate}` : `ATS_${this.currentTemplate}`;
        a.href = url;
        a.download = `${name}_Resume_${suffix}.pdf`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);

        // Refresh user quotas to instantly reflect (e.g. PDFs: 0 left)
        await this.refreshCurrentUser();
      } catch (err) {
        alert('Download Error: ' + err.message);
      } finally {
        this.isDownloading = false;
      }
    },

    async downloadCoverLetterPdf() {
      if (!this.currentUser) {
        this.openAuthModal('register', '🔒 Free Account Required: Sign in or register to download your professional cover letter PDF!');
        return;
      }
      if (!this.tailoredData) return;

      const isFree = !this.currentUser.plan_tier || this.currentUser.plan_tier === 'free';
      if (isFree && this.currentUser.remaining_cover_letter_downloads !== undefined && this.currentUser.remaining_cover_letter_downloads <= 0) {
        this.openQuotaLimitModal({
          title: 'Cover Letter Limit Reached',
          message: 'You have reached the maximum 3 free cover letter downloads.\n\nUpgrade to Pro Career for unlimited watermark-free cover letters!',
          requiredPlan: 'pro'
        });
        return;
      }

      this.isDownloading = true;

      try {
        const token = localStorage.getItem('saas_token');
        const headers = { 'Content-Type': 'application/json' };
        if (token) headers['Authorization'] = `Bearer ${token}`;

        const res = await fetch('/api/generate-pdf/cover-letter', {
          method: 'POST',
          headers: headers,
          body: JSON.stringify(this.tailoredData),
        });

        if (!res.ok) {
          const errData = await res.json().catch(() => null);
          const msg = (errData && errData.detail && errData.detail.message) || (errData && errData.detail) || 'Cover letter download failed';
          if (res.status === 403 || res.status === 402) {
            this.openQuotaLimitModal({
              title: 'Cover Letter Limit Reached',
              message: msg,
              requiredPlan: 'pro'
            });
            return;
          }
          throw new Error(msg);
        }

        const blob = await res.blob();
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        const name = (this.tailoredData.personal_info.full_name || 'Candidate').replace(/\s+/g, '_');
        const comp = (this.tailoredData.target_company || 'Company').replace(/\s+/g, '_');
        a.href = url;
        a.download = `${name}_Cover_Letter_${comp}.pdf`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);

        // Refresh user quotas to instantly reflect (e.g. CL: 2 left)
        await this.refreshCurrentUser();
      } catch (err) {
        alert('Download Error: ' + err.message);
      } finally {
        this.isDownloading = false;
      }
    },

    // Cover Letter & Digital Signature Studio Helpers
    setCoverLetterDateToday() {
      if (!this.tailoredData || !this.tailoredData.cover_letter) return;
      this.tailoredData.cover_letter.letter_date = new Date().toLocaleDateString('en-US', {
        year: 'numeric',
        month: 'long',
        day: 'numeric'
      });
      this.refreshAllPreviews();
    },

    initSigCanvas() {
      const canvas = document.getElementById('sigCanvas');
      if (!canvas) return;
      const ctx = canvas.getContext('2d');
      ctx.strokeStyle = '#1E3A8A';
      ctx.lineWidth = 2.5;
      ctx.lineCap = 'round';
      ctx.lineJoin = 'round';

      let isDrawing = false;
      let lastX = 0;
      let lastY = 0;

      const getPos = (e) => {
        const rect = canvas.getBoundingClientRect();
        const scaleX = canvas.width / rect.width;
        const scaleY = canvas.height / rect.height;
        if (e.touches && e.touches[0]) {
          return {
            x: (e.touches[0].clientX - rect.left) * scaleX,
            y: (e.touches[0].clientY - rect.top) * scaleY
          };
        }
        return {
          x: (e.clientX - rect.left) * scaleX,
          y: (e.clientY - rect.top) * scaleY
        };
      };

      const startDraw = (e) => {
        e.preventDefault();
        isDrawing = true;
        const pos = getPos(e);
        lastX = pos.x;
        lastY = pos.y;
      };

      const draw = (e) => {
        if (!isDrawing) return;
        e.preventDefault();
        const pos = getPos(e);
        ctx.beginPath();
        ctx.moveTo(lastX, lastY);
        ctx.lineTo(pos.x, pos.y);
        ctx.stroke();
        lastX = pos.x;
        lastY = pos.y;
      };

      const stopDraw = () => {
        isDrawing = false;
      };

      canvas.onmousedown = startDraw;
      canvas.onmousemove = draw;
      canvas.onmouseup = stopDraw;
      canvas.onmouseleave = stopDraw;

      canvas.ontouchstart = startDraw;
      canvas.ontouchmove = draw;
      canvas.ontouchend = stopDraw;
    },

    clearSigCanvas() {
      const canvas = document.getElementById('sigCanvas');
      if (!canvas) return;
      const ctx = canvas.getContext('2d');
      ctx.clearRect(0, 0, canvas.width, canvas.height);
      if (this.tailoredData && this.tailoredData.cover_letter) {
        this.tailoredData.cover_letter.signature_image_data = null;
      }
      this.refreshAllPreviews();
    },

    saveSigCanvas() {
      const canvas = document.getElementById('sigCanvas');
      if (!canvas || !this.tailoredData || !this.tailoredData.cover_letter) return;
      const dataUrl = canvas.toDataURL('image/png');
      this.tailoredData.cover_letter.signature_image_data = dataUrl;
      this.refreshAllPreviews();
      alert('✅ Signature captured and applied to your cover letter!');
    },

    handleSigFileUpload(event) {
      const file = event.target.files[0];
      if (!file || !this.tailoredData || !this.tailoredData.cover_letter) return;
      const reader = new FileReader();
      reader.onload = (e) => {
        this.tailoredData.cover_letter.signature_image_data = e.target.result;
        this.refreshAllPreviews();
      };
      reader.readAsDataURL(file);
    },

    getFormattedPlainText() {
      if (!this.tailoredData) return '';
      const d = this.tailoredData;
      const info = d.personal_info;

      let out = `${info.full_name.toUpperCase()}\n`;
      if (d.target_job_title) out += `${d.target_job_title.toUpperCase()}\n`;
      out += `${info.location} | ${info.phone} | ${info.email}\n`;
      if (info.linkedin) out += `LinkedIn: ${info.linkedin}\n`;
      if (info.github) out += `GitHub: ${info.github}\n`;
      if (info.portfolio) out += `Portfolio: ${info.portfolio}\n`;
      
      if (d.show_summary && d.professional_summary) {
        out += `\nPROFESSIONAL SUMMARY\n${d.professional_summary}\n\n`;
      }

      if (d.show_skills && d.skill_categories && d.skill_categories.length > 0) {
        out += `TECHNICAL SKILLS\n`;
        for (const cat of d.skill_categories) {
          out += `${cat.category_name}: ${cat.skills.join(', ')}\n`;
        }
      }

      if (d.show_experience && d.work_experience && d.work_experience.length > 0) {
        out += `\nWORK EXPERIENCE\n`;
        for (const exp of d.work_experience) {
          out += `\n${exp.job_title} - ${exp.company} (${exp.start_date} - ${exp.end_date})\n`;
          for (const bullet of exp.bullet_points) {
            out += `- ${bullet}\n`;
          }
        }
      }

      if (d.show_projects && d.projects && d.projects.length > 0) {
        out += `\nKEY PROJECTS\n`;
        for (const p of d.projects) {
          out += `\n${p.name} [${p.technologies.join(', ')}]\n`;
          if (p.demo_url) out += `Demo: ${p.demo_url}\n`;
          if (p.link) out += `Repo: ${p.link}\n`;
          for (const bullet of p.description_bullets) {
            out += `- ${bullet}\n`;
          }
        }
      }

      if (d.show_education && d.education && d.education.length > 0) {
        out += `\nEDUCATION\n`;
        for (const edu of d.education) {
          out += `${edu.degree} - ${edu.institution} (${edu.graduation_year})\n`;
        }
      }

      if (d.show_certifications && d.certifications && d.certifications.length > 0) {
        out += `\nCERTIFICATIONS & AWARDS\n`;
        for (const cert of d.certifications) {
          out += `${cert.name} - ${cert.issuer} (${cert.year})\n`;
        }
      }

      return out;
    },

    copyPlainText() {
      const text = this.getFormattedPlainText();
      navigator.clipboard.writeText(text).then(() => {
        this.copied = true;
        setTimeout(() => { this.copied = false; }, 2500);
      });
    },

    async checkout(tier) {
      try {
        const res = await fetch('/api/checkout', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ tier: tier }),
        });
        const data = await res.json();
        alert(`Lemon Squeezy Checkout: ${data.message}`);
        this.showPricingModal = false;
      } catch (err) {
        alert('Checkout error: ' + err.message);
      }
    },

    // ─────────────────────────────────────────────────────────────────────────
    // SAAS AUTHENTICATION & MYSQL CLOUD METHODS
    // ─────────────────────────────────────────────────────────────────────────

    openAuthModal(mode = 'login', promptMessage = '') {
      this.authMode = mode;
      this.authError = '';
      this.authPromptMessage = promptMessage;
      this.authForm = { email: '', password: '', full_name: '' };
      this.showAuthModal = true;
      this.$nextTick(() => {
        if (window.lucide) window.lucide.createIcons();
        this.renderGoogleButton();
      });
    },

    async submitAuth() {
      this.authError = '';
      this.isSubmittingAuth = true;

      const endpoint = this.authMode === 'register' ? '/api/auth/register' : '/api/auth/login';
      const payload = {
        email: this.authForm.email,
        password: this.authForm.password,
      };
      if (this.authMode === 'register') {
        payload.full_name = this.authForm.full_name || 'Candidate';
      }

      try {
        const res = await fetch(endpoint, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload),
        });

        const data = await res.json();
        if (!res.ok) {
          throw new Error(data.detail || 'Authentication failed');
        }

        // Save JWT access token
        localStorage.setItem('saas_token', data.access_token);
        this.avatarImgFailed = false;
        this.currentUser = data.user;
        this.showAuthModal = false;

        const wasPendingTailor = (this.pendingAction === 'tailor');
        this.pendingAction = null;
        this.authPromptMessage = '';

        if (wasPendingTailor) {
          // Immediately start tailoring the resume seamlessly!
          this.$nextTick(() => {
            this.tailorResume();
          });
        } else {
          this.welcomeModalData = {
            title: this.authMode === 'register' ? '🎉 Welcome to DreemFolio AI!' : '👋 Welcome Back!',
            message: this.authMode === 'register'
              ? `Your SaaS account for ${data.user.email} is ready. Start optimizing your resume with AI right away!`
              : `Great to see you again, ${data.user.full_name}! All your documents and daily quotas are synced.`
          };
          this.showWelcomeModal = true;
        }
        this.$nextTick(() => { if (window.lucide) window.lucide.createIcons(); });
      } catch (err) {
        this.authError = err.message;
      } finally {
        this.isSubmittingAuth = false;
      }
    },

    // ─────────────────────────────────────────────────────────────────────────
    // GOOGLE OAUTH2 / GOOGLE IDENTITY SERVICES (GIS) METHODS
    // ─────────────────────────────────────────────────────────────────────────
    async initGoogleAuth() {
      try {
        // Ensure Google Identity Services script is present in DOM
        if (!window.google || !window.google.accounts) {
          if (!document.querySelector('script[src*="accounts.google.com/gsi/client"]')) {
            const s = document.createElement('script');
            s.src = 'https://accounts.google.com/gsi/client';
            s.async = true;
            s.defer = true;
            s.onload = () => {
              if (this.showAuthModal) this.renderGoogleButton();
            };
            document.head.appendChild(s);
          }
        }

        const res = await fetch('/api/auth/google-config');
        if (res.ok) {
          const data = await res.json();
          this.googleClientId = data.client_id || '';
          this.isGoogleAuthEnabled = Boolean(data.is_enabled && data.client_id);

          if (this.isGoogleAuthEnabled && window.google && window.google.accounts && window.google.accounts.id) {
            window.google.accounts.id.initialize({
              client_id: this.googleClientId,
              callback: (response) => this.handleGoogleCredentialResponse(response),
              auto_select: false,
              cancel_on_tap_outside: true,
              ux_mode: 'popup'
            });
          }
        }
      } catch (err) {
        console.warn('Could not load Google Auth configuration:', err);
      }
    },

    renderGoogleButton() {
      // Kept for interface compatibility; the single styled popup button is used in UI
    },

    async triggerGoogleSignIn() {
      this.authError = '';
      if (this.isSubmittingGoogleAuth) return;
      this.isSubmittingGoogleAuth = true;

      // Method 2: Launch Google OAuth2 Token Client Popup (Official browser popup window)
      if (this.isGoogleAuthEnabled && window.google && window.google.accounts) {
        if (window.google.accounts.oauth2) {
          try {
            const tokenClient = window.google.accounts.oauth2.initTokenClient({
              client_id: this.googleClientId,
              scope: 'email profile openid',
              callback: async (tokenResponse) => {
                if (tokenResponse && tokenResponse.access_token) {
                  await this.handleGoogleCredentialResponse({
                    credential: tokenResponse.access_token
                  });
                } else {
                  this.isSubmittingGoogleAuth = false;
                }
              },
              error_callback: (err) => {
                console.warn('Google OAuth popup error:', err);
                this.isSubmittingGoogleAuth = false;
                if (err && err.type !== 'popup_closed') {
                  this.authError = 'Google Sign-In popup was blocked or closed.';
                }
              }
            });
            tokenClient.requestAccessToken({ prompt: 'select_account' });
            setTimeout(() => { this.isSubmittingGoogleAuth = false; }, 30000);
            return;
          } catch (oauthErr) {
            console.warn('OAuth token client init failed, trying ID prompt:', oauthErr);
          }
        }

        // Method 3: Google One Tap prompt with instant feedback
        window.google.accounts.id.initialize({
          client_id: this.googleClientId,
          callback: (response) => this.handleGoogleCredentialResponse(response),
          auto_select: false,
          cancel_on_tap_outside: true,
          ux_mode: 'popup'
        });

        window.google.accounts.id.prompt((notification) => {
          if (notification.isNotDisplayed()) {
            this.isSubmittingGoogleAuth = false;
            const reason = notification.getNotDisplayedReason() || 'suppressed';
            this.authError = `Google prompt was suppressed by browser (${reason}). Please click the Google Sign In button directly or use Email.`;
          } else if (notification.isSkippedMoment()) {
            this.isSubmittingGoogleAuth = false;
          }
        });
      } else {
        this.isSubmittingGoogleAuth = false;
        // Fallback for development/setup when Client ID has not been pasted in /paneladmin yet
        const promptSimulate = confirm(
          "⚙️ Google Sign-In Notice\n\n" +
          "Connecting to Google Identity Services.\n\n" +
          "Would you like to sign in using a verified Google candidate profile right now?"
        );
        if (promptSimulate) {
          const mockId = 'google_' + Math.floor(100000 + Math.random() * 900000);
          const mockEmail = `candidate_${Math.floor(1000 + Math.random() * 9000)}@gmail.com`;
          await this.handleGoogleCredentialResponse({
            credential: `mock_google_token_:${mockId}:${mockEmail}:Google Candidate:https://lh3.googleusercontent.com/a/default-user=s96-c`
          });
        }
      }
    },

    async handleGoogleCredentialResponse(googleResponse) {
      if (!googleResponse || !googleResponse.credential) {
        this.authError = 'Google authentication response did not contain a valid credential.';
        return;
      }

      this.isSubmittingGoogleAuth = true;
      this.authError = '';

      try {
        const res = await fetch('/api/auth/google', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            credential: googleResponse.credential,
            client_id: this.googleClientId || null
          })
        });

        const rawText = await res.text();
        let data = {};
        try {
          data = JSON.parse(rawText);
        } catch (jsonErr) {
          throw new Error(`Authentication server error (${res.status}): ${rawText || 'Unexpected response'}`);
        }

        if (!res.ok) {
          throw new Error(data.detail || 'Google sign-in failed. Please try again.');
        }

        // Securely store SaaS token
        localStorage.setItem('saas_token', data.access_token);
        this.avatarImgFailed = false;
        this.currentUser = data.user;
        this.showAuthModal = false;

        const wasPendingTailor = (this.pendingAction === 'tailor');
        this.pendingAction = null;
        this.authPromptMessage = '';

        if (wasPendingTailor) {
          this.$nextTick(() => { this.tailorResume(); });
        } else {
          this.welcomeModalData = {
            title: '🎉 Google Sign-In Successful!',
            message: `Welcome, ${data.user.full_name}! You are authenticated via Google (${data.user.email}). Start optimizing your ATS resumes right away!`
          };
          this.showWelcomeModal = true;
        }
        this.$nextTick(() => { if (window.lucide) window.lucide.createIcons(); });
      } catch (err) {
        this.authError = err.message;
      } finally {
        this.isSubmittingGoogleAuth = false;
      }
    },

    logout() {
      this.showLogoutModal = true;
      this.$nextTick(() => { if (window.lucide) window.lucide.createIcons(); });
    },

    confirmLogout() {
      this.showLogoutModal = false;
      this.showQuotaDropdown = false;
      localStorage.removeItem('saas_token');
      this.currentUser = null;
      this.$nextTick(() => { if (window.lucide) window.lucide.createIcons(); });
    },

    async loadDynamicPlans(countryCode = null) {
      try {
        const code = countryCode || this.activeCountryCode || 'LK';
        const res = await fetch(`/api/subscription/plans?country=${encodeURIComponent(code)}`);
        if (res.ok) {
          const data = await res.json();
          if (data.plans && data.plans.length > 0) {
            this.dynamicPlans = data.plans;
          }
          if (data.country_code) this.activeCountryCode = data.country_code;
          if (data.currency) this.activeCurrency = data.currency;
          if (data.currency_symbol) this.activeCurrencySymbol = data.currency_symbol;
          if (data.sprint_price) this.activeSprintPrice = data.sprint_price;
          if (data.available_countries) this.availableCountries = data.available_countries;
          this.$nextTick(() => { if (window.lucide) window.lucide.createIcons(); });
        }
      } catch (err) {
        console.warn('Could not fetch dynamic plans:', err);
      }
    },

    async selectCountryCurrency(countryCode) {
      this.activeCountryCode = countryCode;
      await this.loadDynamicPlans(countryCode);
    },

    async saveResumeToMySQL() {
      if (!this.currentUser) {
        this.openAuthModal('login');
        return;
      }
      if (!this.tailoredData) {
        alert('Please generate or customize a resume first before saving.');
        return;
      }

      this.isSavingResume = true;
      const token = localStorage.getItem('saas_token');

      try {
        const res = await fetch('/api/user/resumes', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${token}`
          },
          body: JSON.stringify({
            title: `${this.tailoredData.target_job_title} - ${this.tailoredData.target_company || 'Target Role'}`,
            resume_data: this.tailoredData
          })
        });

        const data = await res.json();
        if (!res.ok) throw new Error(data.detail || 'Failed to save resume');

        alert(`✅ Success! Your resume was securely auto-saved to MySQL Cloud Database (ID: #${data.resume_id}).`);
      } catch (err) {
        alert('Save Error: ' + err.message);
      } finally {
        this.isSavingResume = false;
      }
    },

    openProRestoreModal(resumeItem) {
      this.pendingRestoreResume = resumeItem;
      this.showProRestoreModal = true;
      this.$nextTick(() => { if (window.lucide) window.lucide.createIcons(); });
    },

    upgradePlan(targetPlan, durationMonths = 1) {
      return this.upgradeSubscription(targetPlan, durationMonths);
    },

    async openSavedResumesModal() {
      if (!this.currentUser) {
        this.openAuthModal('login');
        return;
      }

      this.showSavedResumesModal = true;
      this.isLoadingSavedResumes = true;
      this.$nextTick(() => { if (window.lucide) window.lucide.createIcons(); });

      const token = localStorage.getItem('saas_token');
      try {
        const res = await fetch('/api/user/resumes', {
          headers: { 'Authorization': `Bearer ${token}` }
        });
        if (res.ok) {
          this.userSavedResumes = await res.json();
        } else {
          throw new Error('Failed to load resumes');
        }
      } catch (err) {
        console.warn('Could not fetch saved resumes:', err);
      } finally {
        this.isLoadingSavedResumes = false;
        this.$nextTick(() => { if (window.lucide) window.lucide.createIcons(); });
      }
    },

    async loadSavedResume(id) {
      const isFree = !this.currentUser?.plan_tier || this.currentUser?.plan_tier === 'free';
      if (isFree) {
        const found = this.userSavedResumes.find(r => r.id === id);
        this.openProRestoreModal(found || { title: 'Saved Resume' });
        return;
      }

      const token = localStorage.getItem('saas_token');
      try {
        const res = await fetch(`/api/user/resumes/${id}`, {
          headers: { 'Authorization': `Bearer ${token}` }
        });
        if (res.status === 403) {
          const found = this.userSavedResumes.find(r => r.id === id);
          this.openProRestoreModal(found || { title: 'Saved Resume' });
          return;
        }
        if (!res.ok) throw new Error('Could not load resume from MySQL');

        const result = await res.json();
        const loadedResume = result.resume_data || result;
        this.currentResumeId = result.resume_id || id;
        this.autoSaveStatus = 'saved';
        this.lastSavedTime = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });

        this.tailoredData = loadedResume;
        this.targetJobTitle = loadedResume.target_job_title || '';
        this.targetCompany = loadedResume.target_company || '';
        this.currentTemplate = loadedResume.template_style || 'visual_sidebar';
        this.portfolioTheme = loadedResume.portfolio_theme || 'bento_grid';
        this.portfolioAccent = loadedResume.portfolio_accent_color || '#6366f1';
        this.portfolioFont = loadedResume.portfolio_font || 'Inter';

        if (!loadedResume.portfolio_metrics || loadedResume.portfolio_metrics.length === 0) {
          loadedResume.portfolio_metrics = [
            { label: 'Key Projects', value: (loadedResume.projects?.length || 10) + '+' },
            { label: 'Experience', value: (loadedResume.work_experience?.length || 5) + '+ Yrs' },
            { label: 'System Uptime', value: '99.98%' },
            { label: 'Stack Skills', value: '25+' }
          ];
        }

        this.showSavedResumesModal = false;
        await this.refreshAllPreviews();
      } catch (err) {
        alert('Load Error: ' + err.message);
      }
    },

    async deleteSavedResume(id) {
      if (!confirm('Are you sure you want to delete this resume from MySQL?')) return;
      const token = localStorage.getItem('saas_token');
      try {
        const res = await fetch(`/api/user/resumes/${id}`, {
          method: 'DELETE',
          headers: { 'Authorization': `Bearer ${token}` }
        });
        if (!res.ok) throw new Error('Delete failed');

        this.userSavedResumes = this.userSavedResumes.filter(r => r.id !== id);
        this.$nextTick(() => { if (window.lucide) window.lucide.createIcons(); });
      } catch (err) {
        alert('Delete Error: ' + err.message);
      }
    },

    async upgradeSubscription(targetPlan, durationMonths = 1) {
      if (!this.currentUser) {
        this.openAuthModal('login');
        return;
      }

      this.isSubmittingUpgrade = true;
      const token = localStorage.getItem('saas_token');
      try {
        const res = await fetch('/api/subscription/upgrade', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${token}`
          },
          body: JSON.stringify({
            plan_tier: targetPlan,
            duration_months: durationMonths,
            payment_method: 'card'
          })
        });

        if (!res.ok) {
          const err = await res.json();
          throw new Error(typeof err.detail === 'object' ? JSON.stringify(err.detail) : (err.detail || 'Upgrade failed'));
        }

        const updatedUser = await res.json();
        this.currentUser = updatedUser;
        this.showPricingModal = false;
        alert(`🎉 Congratulations! Your SaaS account has been upgraded to ${targetPlan.toUpperCase()} with full privileges!`);
        this.$nextTick(() => { if (window.lucide) window.lucide.createIcons(); });
      } catch (err) {
        alert('Upgrade Error: ' + err.message);
      } finally {
        this.isSubmittingUpgrade = false;
      }
    },

    // ─────────────────────────────────────────────────────────────────────────
    // ENTERPRISE SAAS ADMIN METHODS
    // ─────────────────────────────────────────────────────────────────────────
    async openAdminModal() {
      if (!this.currentUser || !this.currentUser.is_admin) {
        alert('Administrator access required.');
        return;
      }
      this.showAdminModal = true;
      this.adminActiveTab = 'overview';
      this.$nextTick(() => { if (window.lucide) window.lucide.createIcons(); });
      await Promise.all([
        this.loadAdminOverview(),
        this.loadAdminSettings(),
        this.loadAdminUsers()
      ]);
    },

    async loadAdminOverview() {
      this.isLoadingAdminOverview = true;
      const token = localStorage.getItem('saas_token');
      try {
        const res = await fetch('/api/admin/overview', {
          headers: { 'Authorization': `Bearer ${token}` }
        });
        if (res.ok) {
          this.adminOverview = await res.json();
        }
      } catch (err) {
        console.error('Failed to load admin overview:', err);
      } finally {
        this.isLoadingAdminOverview = false;
        this.$nextTick(() => { if (window.lucide) window.lucide.createIcons(); });
      }
    },

    async loadAdminSettings() {
      const token = localStorage.getItem('saas_token');
      try {
        const res = await fetch('/api/admin/settings', {
          headers: { 'Authorization': `Bearer ${token}` }
        });
        if (res.ok) {
          const settings = await res.json();
          for (const s of settings) {
            if (s.key === 'free_allow_visual_download' || s.key === 'free_allow_cloud_restore') {
              this.adminSettingsState[s.key] = (s.value === 'true');
            } else {
              this.adminSettingsState[s.key] = s.value;
            }
          }
        }
      } catch (err) {
        console.error('Failed to load admin settings:', err);
      }
    },

    async saveAdminSettings() {
      this.isSavingAdminSettings = true;
      this.adminSettingsSaveMsg = '';
      const token = localStorage.getItem('saas_token');
      const payload = {
        settings: {
          free_daily_ai_limit: String(this.adminSettingsState.free_daily_ai_limit),
          free_daily_pdf_limit: String(this.adminSettingsState.free_daily_pdf_limit),
          free_allow_visual_download: String(this.adminSettingsState.free_allow_visual_download),
          free_allow_cloud_restore: String(this.adminSettingsState.free_allow_cloud_restore),
          pro_monthly_price: String(this.adminSettingsState.pro_monthly_price),
          elite_monthly_price: String(this.adminSettingsState.elite_monthly_price),
          sprint_price: String(this.adminSettingsState.sprint_price)
        }
      };

      try {
        const res = await fetch('/api/admin/settings/update', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${token}`
          },
          body: JSON.stringify(payload)
        });
        if (!res.ok) {
          const err = await res.json();
          throw new Error(err.detail || 'Failed to save settings');
        }
        this.adminSettingsSaveMsg = '✅ SaaS Rules saved successfully!';
        setTimeout(() => { this.adminSettingsSaveMsg = ''; }, 3500);
      } catch (err) {
        this.adminSettingsSaveMsg = '❌ ' + err.message;
      } finally {
        this.isSavingAdminSettings = false;
      }
    },

    async loadAdminUsers() {
      this.isLoadingAdminUsers = true;
      const token = localStorage.getItem('saas_token');
      try {
        const res = await fetch('/api/admin/users', {
          headers: { 'Authorization': `Bearer ${token}` }
        });
        if (res.ok) {
          this.adminUsersList = await res.json();
        }
      } catch (err) {
        console.error('Failed to load admin users:', err);
      } finally {
        this.isLoadingAdminUsers = false;
        this.$nextTick(() => { if (window.lucide) window.lucide.createIcons(); });
      }
    },

    async adminChangeUserPlan(userId, newPlan) {
      const token = localStorage.getItem('saas_token');
      try {
        const res = await fetch(`/api/admin/users/${userId}/plan`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${token}`
          },
          body: JSON.stringify({ plan_tier: newPlan, duration_days: 30 })
        });
        if (!res.ok) throw new Error('Failed to update user plan');
        await this.loadAdminUsers();
        await this.loadAdminOverview();
      } catch (err) {
        alert('Plan Override Error: ' + err.message);
      }
    },

    async adminExtendUserPlan(userId, days = 30) {
      const token = localStorage.getItem('saas_token');
      try {
        const user = this.adminUsersList.find(u => u.id === userId);
        const targetPlan = (user && user.plan_tier !== 'free') ? user.plan_tier : 'pro';
        const res = await fetch(`/api/admin/users/${userId}/plan`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${token}`
          },
          body: JSON.stringify({ plan_tier: targetPlan, duration_days: days })
        });
        if (!res.ok) throw new Error('Failed to extend subscription');
        await this.loadAdminUsers();
        await this.loadAdminOverview();
        alert(`✅ User #${userId} subscription extended by +${days} days!`);
      } catch (err) {
        alert('Extension Error: ' + err.message);
      }
    },

    selectJobToTailor(job) {
      if (!job) return;
      this.targetJobTitle = job.title || '';
      this.targetCompany = job.company_type || '';
      this.jobDescription = `Role: ${job.title}\nIndustry / Sector: ${job.company_type || 'General'}\nWork Mode: ${job.work_mode || 'Remote'}\nExperience Level: ${job.experience_level || 'Mid-Senior'}\nRequired & Preferred Competencies:\n- ${(job.key_skills || []).join('\n- ')}\n\nProfile Fit Rationale:\n${job.match_reason || ''}`;
      
      // Auto-scroll into Step 2 inputs smoothly
      this.$nextTick(() => {
        const step2 = document.querySelector('input[x-model="targetJobTitle"]') || document.getElementById('step-2') || document.querySelector('[data-step="2"]');
        if (step2) {
          step2.scrollIntoView({ behavior: 'smooth', block: 'center' });
          step2.focus();
        }
      });
    },

    getJobSearchUrl(platform, job) {
      if (!job) return '#';
      const q = encodeURIComponent(job.search_keywords || job.title);
      if (platform === 'linkedin') {
        return `https://www.linkedin.com/jobs/search/?keywords=${q}`;
      } else if (platform === 'indeed') {
        return `https://www.indeed.com/jobs?q=${q}`;
      } else if (platform === 'google') {
        return `https://www.google.com/search?q=${q}+jobs`;
      }
      return `https://www.google.com/search?q=${q}+jobs`;
    },

    async openApplicationCopilot(job) {
      if (!job) return;

      if (this.currentUser && this.currentUser.plan_tier === 'free' && this.currentUser.daily_copilot_kits_remaining === 0) {
        this.openQuotaLimitModal({
          title: 'Application Copilot Limit Reached',
          message: 'Free Starter tier includes 1 tailored Application Kit per day. Upgrade to Pro ($9/mo) for unlimited 1-click tailored screening answers & elevator pitches!',
          feature: 'application_copilot',
          requiredPlan: 'pro'
        });
        return;
      }

      this.currentCopilotJob = job;
      this.showCopilotModal = true;
      this.copilotKit = null;
      this.isLoadingCopilot = true;
      this.copiedKey = '';
      this.$nextTick(() => { if (window.lucide) window.lucide.createIcons(); });
      
      try {
        const token = localStorage.getItem('saas_token');
        const res = await fetch('/api/jobs/application-kit', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            ...(token ? { 'Authorization': `Bearer ${token}` } : {})
          },
          body: JSON.stringify({
            job_title: job.title,
            company_name: job.company_type || job.company || 'Target Company',
            job_description: job.match_reason || '',
            work_mode: job.work_mode || 'Remote',
            salary_range: job.estimated_salary || job.salary || null,
            resume_data: this.tailoredData || null
          })
        });
        if (res.status === 402) {
          this.showCopilotModal = false;
          this.openQuotaLimitModal({
            title: 'Daily Application Kit Limit Reached',
            message: 'You have used your free application kit for today. Upgrade to Pro ($9/mo) for unlimited 1-click screening kits!',
            feature: 'application_copilot',
            requiredPlan: 'pro'
          });
          return;
        }
        if (!res.ok) throw new Error('Failed to generate application kit');
        this.copilotKit = await res.json();
        await this.refreshCurrentUser();
      } catch (err) {
        console.warn('Copilot kit generation error:', err);
        this.copilotKit = {
          job_title: job.title,
          company_name: job.company_type || job.company || 'Target Company',
          elevator_pitch: `I am a skilled professional with proven capabilities in ${(job.key_skills || job.tags || ['Software Engineering']).join(', ')}. In my recent work, I have consistently delivered robust, high-impact results while collaborating across teams. I am eager to apply my problem-solving methodology to ${job.company_type || job.company || 'your team'} as ${job.title}.`,
          why_company: `The engineering quality and mission at ${job.company_type || job.company || 'your company'} strongly align with my background. I am confident that my technical skills and proactive ownership will allow me to deliver immediate value for this role.`,
          key_achievement: `Architected and delivered mission-critical features, reduced latency, and optimized application workflows on schedule.`,
          salary_expectation_answer: `Based on the responsibilities of this ${job.title} role and current market benchmarks, I am targeting ${job.estimated_salary || job.salary || '$105k - $140k / yr'}, but I am open to discussing the complete package.`,
          availability_notice_answer: `I am available to commence employment within a standard 2 to 4-week transition period.`,
          strengths_summary: [
            `Demonstrated proficiency in ${(job.key_skills || job.tags || ['Core Competencies']).slice(0, 3).join(', ')}`,
            `Track record of high-impact delivery and continuous improvement`,
            `Autonomous execution in ${job.work_mode || 'Remote'} environments`
          ],
          recommended_custom_qa: [
            {
              question: 'How do you approach learning new technologies quickly?',
              answer: 'I combine documentation deep dives with hands-on prototyping. I build proof-of-concepts, follow best practices, and study production patterns to rapidly achieve delivery velocity.'
            }
          ]
        };
      } finally {
        this.isLoadingCopilot = false;
        this.$nextTick(() => { if (window.lucide) window.lucide.createIcons(); });
      }
    },

    copyCopilotAnswer(text, key) {
      if (!text) return;
      navigator.clipboard.writeText(text);
      this.copiedKey = key;
      setTimeout(() => {
        if (this.copiedKey === key) this.copiedKey = '';
      }, 2000);
    },

    async saveJobToTracker(job, status = 'wishlist') {
      if (!job) return;
      const token = localStorage.getItem('saas_token');
      if (!token) {
        this.openAuthModal('login', 'Please sign in to save and track your job applications in MySQL!');
        return;
      }

      if (this.currentUser && (this.currentUser.plan_tier === 'free' || !this.currentUser.plan_tier) && this.userTrackedJobs.length >= 3) {
        this.openQuotaLimitModal({
          title: 'Job Tracker Quota Reached (3/3 Jobs)',
          message: 'Free Starter tier allows tracking up to 3 job applications. Upgrade to Pro ($9/mo) for unlimited Kanban pipeline job tracking and cloud sync!',
          feature: 'job_tracker',
          requiredPlan: 'pro'
        });
        return;
      }

      try {
        const res = await fetch('/api/user/job-tracker', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${token}`
          },
          body: JSON.stringify({
            job_title: job.title,
            company_name: job.company_type || job.company || 'Target Company',
            location: job.location || (this.tailoredData?.personal_info?.location || 'Remote'),
            work_mode: job.work_mode || 'Remote',
            salary_range: job.estimated_salary || job.salary || null,
            match_score: job.match_score || 95,
            job_url: job.easy_apply_url || job.apply_url || null,
            status: status,
            application_kit_json: this.copilotKit ? JSON.stringify(this.copilotKit) : null
          })
        });
        if (res.status === 402) {
          this.openQuotaLimitModal({
            title: 'Job Tracker Quota Reached (3/3 Jobs)',
            message: 'Free Starter tier allows tracking up to 3 job applications. Upgrade to Pro ($9/mo) for unlimited Kanban pipeline job tracking!',
            feature: 'job_tracker',
            requiredPlan: 'pro'
          });
          return;
        }
        if (!res.ok) throw new Error('Failed to save to tracker');
        await this.loadUserTrackedJobs();
        alert(`✅ "${job.title}" saved to your Application Tracker (${status.toUpperCase()})!`);
      } catch (err) {
        alert('Tracker Error: ' + err.message);
      }
    },

    async loadUserTrackedJobs() {
      const token = localStorage.getItem('saas_token');
      if (!token) return;
      this.isLoadingTrackedJobs = true;
      try {
        const res = await fetch('/api/user/job-tracker', {
          headers: { 'Authorization': `Bearer ${token}` }
        });
        if (res.ok) {
          this.userTrackedJobs = await res.json();
        }
      } catch (err) {
        console.warn('Failed to load tracked jobs:', err);
      } finally {
        this.isLoadingTrackedJobs = false;
        this.$nextTick(() => { if (window.lucide) window.lucide.createIcons(); });
      }
    },

    async updateTrackedJobStatus(jobId, newStatus) {
      const token = localStorage.getItem('saas_token');
      if (!token) return;
      try {
        const res = await fetch(`/api/user/job-tracker/${jobId}`, {
          method: 'PATCH',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${token}`
          },
          body: JSON.stringify({ status: newStatus })
        });
        if (res.ok) {
          await this.loadUserTrackedJobs();
        }
      } catch (err) {
        alert('Failed to update job status: ' + err.message);
      }
    },

    async deleteTrackedJob(jobId) {
      if (!confirm('Are you sure you want to remove this job from your tracker?')) return;
      const token = localStorage.getItem('saas_token');
      if (!token) return;
      try {
        const res = await fetch(`/api/user/job-tracker/${jobId}`, {
          method: 'DELETE',
          headers: { 'Authorization': `Bearer ${token}` }
        });
        if (res.ok) {
          await this.loadUserTrackedJobs();
        }
      } catch (err) {
        alert('Failed to delete job: ' + err.message);
      }
    },

    async performLiveJobSearch() {
      const q = this.jobSearchQuery.keywords || this.tailoredData?.target_job_title || 'Software Engineer';
      const loc = this.jobSearchQuery.location || 'Remote';
      this.isSearchingJobs = true;
      try {
        const res = await fetch('/api/jobs/search', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            keywords: q,
            location: loc,
            work_mode: this.jobSearchQuery.work_mode || 'all',
            experience_level: this.jobSearchQuery.experience_level || 'all',
            limit: 8
          })
        });
        if (!res.ok) throw new Error('Search request failed');
        const data = await res.json();
        this.jobSearchResults = data.results || [];
      } catch (err) {
        console.warn('Live search error:', err);
      } finally {
        this.isSearchingJobs = false;
        this.$nextTick(() => { if (window.lucide) window.lucide.createIcons(); });
      }
    },

    // ── AI Career Copilot Chatbot Methods ─────────────────────────
    toggleChatBot() {
      this.showChatBot = !this.showChatBot;
      if (this.showChatBot) {
        this.$nextTick(() => {
          this.scrollChatToBottom();
          if (window.lucide) window.lucide.createIcons();
        });
      }
    },

    clearChat() {
      this.chatMessages = [];
      this.suggestedPrompts = [
        'Conduct a realistic technical mock interview for my role',
        'Critique my resume bullets with the Google XYZ formula',
        'Draft a personalized LinkedIn DM to a hiring manager',
        'Give me a strategic salary negotiation script'
      ];
      this.$nextTick(() => {
        if (window.lucide) window.lucide.createIcons();
      });
    },

    scrollChatToBottom() {
      const container = document.getElementById('copilot-messages-container');
      if (container) {
        container.scrollTop = container.scrollHeight;
      }
    },

    formatChatMessage(text) {
      if (!text) return '';
      // Escape basic HTML entities
      let sanitized = text
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;');

      // Markdown bold: **text**
      sanitized = sanitized.replace(/\*\*(.*?)\*\*/g, '<strong class="font-semibold text-white">$1</strong>');
      // Markdown italic: *text*
      sanitized = sanitized.replace(/\*(.*?)\*/g, '<em class="text-slate-300">$1</em>');
      // Markdown inline code: `code`
      sanitized = sanitized.replace(/`([^`]+)`/g, '<code class="px-1.5 py-0.5 rounded bg-slate-950 text-indigo-300 font-mono text-[11px]">$1</code>');
      // Markdown bullet lists: - item or * item
      sanitized = sanitized.replace(/^\s*[-*]\s+(.*)$/gm, '<li class="ml-4 list-disc text-slate-300 my-0.5">$1</li>');
      // Double newlines into paragraph breaks
      sanitized = sanitized.replace(/\n\n/g, '<div class="h-2"></div>');
      // Single newlines into breaks
      sanitized = sanitized.replace(/\n/g, '<br/>');
      return sanitized;
    },

    copyTextToClipboard(text) {
      if (!text) return;
      navigator.clipboard.writeText(text).catch(err => console.warn('Copy failed:', err));
    },

    async sendChatMessage(promptText = null) {
      const query = (promptText || this.chatInput || '').trim();
      if (!query || this.isChatLoading) return;

      const userTime = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
      
      // Append user message immediately
      this.chatMessages.push({
        role: 'user',
        content: query,
        timestamp: userTime
      });

      this.chatInput = '';
      this.isChatLoading = true;

      this.$nextTick(() => {
        this.scrollChatToBottom();
        if (window.lucide) window.lucide.createIcons();
      });

      try {
        const payload = {
          messages: this.chatMessages.map(m => ({ role: m.role, content: m.content })),
          resume_context: this.tailoredData || null,
          target_job_title: this.targetJobTitle || (this.tailoredData?.target_job_title || ''),
          company_name: this.targetCompany || ''
        };

        const token = localStorage.getItem('saas_token');
        const res = await fetch('/api/chat/copilot', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            ...(token ? { 'Authorization': `Bearer ${token}` } : {})
          },
          body: JSON.stringify(payload)
        });

        if (!res.ok) {
          throw new Error(`Server returned HTTP ${res.status}`);
        }

        const data = await res.json();
        const replyTime = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });

        this.chatMessages.push({
          role: 'assistant',
          content: data.reply,
          timestamp: replyTime,
          action_trigger: data.action_trigger || null
        });

        await this.refreshCurrentUser();

        if (data.suggested_prompts && data.suggested_prompts.length > 0) {
          this.suggestedPrompts = data.suggested_prompts;
        }

      } catch (err) {
        console.error('Chat Copilot error:', err);
        this.chatMessages.push({
          role: 'assistant',
          content: "⚠️ I encountered an issue communicating with the AI service. Here is a quick tip: Try rephrasing your question or pick one of the quick starter prompts below.",
          timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
        });
      } finally {
        this.isChatLoading = false;
        this.$nextTick(() => {
          this.scrollChatToBottom();
          if (window.lucide) window.lucide.createIcons();
        });
      }
    },

    // ═══════════════════════════════════════════════════════════════════
    // AI VOICE MOCK INTERVIEW SIMULATOR STUDIO METHODS
    // ═══════════════════════════════════════════════════════════════════

    openVoiceInterviewModal(role = '', company = '') {
      const activeRole = role || this.tailoredData?.target_job_title || this.targetJobTitle || 'Automotive Technician';
      const activeCompany = company || this.targetCompany || '';

      this.interviewTargetRole = activeRole;
      this.interviewTargetCompany = activeCompany;
      this.interviewStep = 'setup';
      this.interviewQuestions = [];
      this.currentQuestionIndex = 0;
      this.currentQuestion = null;
      this.sessionEvaluations = [];
      this.candidateAnswerTranscript = '';
      this.finalReport = null;
      this.voiceInterviewModalOpen = true;

      this.$nextTick(() => {
        if (window.lucide) window.lucide.createIcons();
      });
    },

    closeVoiceInterviewModal() {
      this.stopCandidateRecording();
      if (window.speechSynthesis) {
        window.speechSynthesis.cancel();
      }
      this.isInterviewerSpeaking = false;
      this.voiceInterviewModalOpen = false;
    },

    async startVoiceInterviewSession() {
      if (!this.interviewTargetRole.trim()) {
        this.interviewTargetRole = 'Professional';
      }

      this.isStartingInterview = true;
      const token = localStorage.getItem('saas_token');

      try {
        const payload = {
          target_role: this.interviewTargetRole,
          target_company: this.interviewTargetCompany || null,
          interview_type: this.interviewType || 'behavioral',
          difficulty: this.interviewDifficulty || 'standard',
          question_count: parseInt(this.interviewQuestionCount, 10) || 3,
          resume_context: this.tailoredData || null
        };

        const res = await fetch('/api/interview/start', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            ...(token ? { 'Authorization': `Bearer ${token}` } : {})
          },
          body: JSON.stringify(payload)
        });

        if (res.status === 403) {
          const errData = await res.json().catch(() => ({}));
          this.closeVoiceInterviewModal();
          this.openQuotaLimitModal({
            title: 'Voice Interview Quota Reached',
            message: errData.detail?.message || 'Free tier includes 1 AI Voice Mock Interview per day. Upgrade to Pro for unlimited full-length sessions!',
            feature: 'voice_mock_interview',
            requiredPlan: 'pro'
          });
          return;
        }

        if (!res.ok) {
          throw new Error(`Server error: ${res.status}`);
        }

        const data = await res.json();
        this.interviewSessionId = data.session_id;
        this.interviewQuestions = data.questions || [];
        this.currentQuestionIndex = 0;
        this.currentQuestion = this.interviewQuestions[0] || null;
        this.sessionEvaluations = [];
        this.candidateAnswerTranscript = '';
        this.recordingDurationSeconds = 0;
        this.interviewStep = 'interviewing';

        this.$nextTick(() => {
          if (window.lucide) window.lucide.createIcons();
          // Speak first question after a short UI transition delay
          setTimeout(() => {
            this.speakCurrentQuestion();
          }, 400);
        });

      } catch (err) {
        console.error('Failed to start mock interview:', err);
        alert('Could not start mock interview session. Please try again.');
      } finally {
        this.isStartingInterview = false;
      }
    },

    speakCurrentQuestion() {
      if (!this.currentQuestion || !window.speechSynthesis) return;

      window.speechSynthesis.cancel();
      const textToSpeak = this.currentQuestion.question_text;
      const utterance = new SpeechSynthesisUtterance(textToSpeak);

      utterance.rate = 0.95;
      utterance.pitch = 1.0;

      // Select natural English voice if available
      const voices = window.speechSynthesis.getVoices();
      const engVoice = voices.find(v => v.lang.startsWith('en') && (v.name.includes('Natural') || v.name.includes('Google') || v.name.includes('Samantha') || v.name.includes('Daniel')));
      if (engVoice) {
        utterance.voice = engVoice;
      }

      this.isInterviewerSpeaking = true;

      utterance.onend = () => {
        this.isInterviewerSpeaking = false;
      };
      utterance.onerror = () => {
        this.isInterviewerSpeaking = false;
      };

      window.speechSynthesis.speak(utterance);
    },

    startCandidateRecording() {
      const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;

      if (!SpeechRecognition) {
        this.showManualTextInput = true;
        alert('Live speech recognition is not supported in this browser. You can type or edit your answer directly in the text editor!');
        return;
      }

      // Stop any AI interviewer speech
      if (window.speechSynthesis) {
        window.speechSynthesis.cancel();
      }
      this.isInterviewerSpeaking = false;

      try {
        if (!this.speechRecognitionInstance) {
          const recognition = new SpeechRecognition();
          recognition.continuous = true;
          recognition.interimResults = true;
          recognition.lang = 'en-US';

          let finalTrans = this.candidateAnswerTranscript || '';

          recognition.onresult = (event) => {
            let interim = '';
            for (let i = event.resultIndex; i < event.results.length; ++i) {
              if (event.results[i].isFinal) {
                finalTrans += (finalTrans ? ' ' : '') + event.results[i][0].transcript.trim();
              } else {
                interim += event.results[i][0].transcript;
              }
            }
            this.candidateAnswerTranscript = (finalTrans + (interim ? ' ' + interim : '')).trim();
          };

          recognition.onerror = (event) => {
            console.warn('Speech recognition event error:', event.error);
            if (event.error === 'not-allowed') {
              this.showManualTextInput = true;
              alert('Microphone access was denied. Please allow microphone permissions or type your answer.');
              this.stopCandidateRecording();
            }
          };

          recognition.onend = () => {
            if (this.isRecordingAnswer) {
              // Auto-restart if user is still in recording mode
              try { recognition.start(); } catch (e) {}
            }
          };

          this.speechRecognitionInstance = recognition;
        }

        this.speechRecognitionInstance.start();
        this.isRecordingAnswer = true;

        if (this.recordingTimerInterval) clearInterval(this.recordingTimerInterval);
        this.recordingTimerInterval = setInterval(() => {
          this.recordingDurationSeconds++;
        }, 1000);

      } catch (err) {
        console.warn('Error starting speech recognition:', err);
        this.showManualTextInput = true;
      }
    },

    stopCandidateRecording() {
      this.isRecordingAnswer = false;
      if (this.recordingTimerInterval) {
        clearInterval(this.recordingTimerInterval);
        this.recordingTimerInterval = null;
      }
      if (this.speechRecognitionInstance) {
        try {
          this.speechRecognitionInstance.stop();
        } catch (e) {}
        this.speechRecognitionInstance = null;
      }
    },

    formatSeconds(seconds) {
      const mins = Math.floor(seconds / 60);
      const secs = seconds % 60;
      return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
    },

    async submitAnswerForCritique() {
      this.stopCandidateRecording();
      if (!this.candidateAnswerTranscript || this.candidateAnswerTranscript.trim().length < 5) return;

      this.isEvaluatingAnswer = true;
      const token = localStorage.getItem('saas_token');

      try {
        const payload = {
          session_id: this.interviewSessionId,
          question_id: this.currentQuestion?.id || (this.currentQuestionIndex + 1),
          question_text: this.currentQuestion?.question_text || '',
          candidate_answer_transcript: this.candidateAnswerTranscript,
          duration_seconds: Math.max(this.recordingDurationSeconds, 10),
          target_role: this.interviewTargetRole,
          interview_type: this.interviewType
        };

        const res = await fetch('/api/interview/evaluate-answer', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            ...(token ? { 'Authorization': `Bearer ${token}` } : {})
          },
          body: JSON.stringify(payload)
        });

        if (!res.ok) throw new Error(`HTTP ${res.status}`);

        const evalData = await res.json();
        this.currentEvaluation = evalData;
        this.sessionEvaluations.push(evalData);
        this.interviewStep = 'critique';

        this.$nextTick(() => {
          if (window.lucide) window.lucide.createIcons();
        });

      } catch (err) {
        console.error('Answer evaluation failed:', err);
        alert('Failed to evaluate answer. Please try again.');
      } finally {
        this.isEvaluatingAnswer = false;
      }
    },

    proceedToNextQuestionOrReport() {
      if (this.currentQuestionIndex + 1 < this.interviewQuestions.length) {
        this.currentQuestionIndex++;
        this.currentQuestion = this.interviewQuestions[this.currentQuestionIndex];
        this.candidateAnswerTranscript = '';
        this.recordingDurationSeconds = 0;
        this.currentEvaluation = null;
        this.interviewStep = 'interviewing';

        this.$nextTick(() => {
          if (window.lucide) window.lucide.createIcons();
          setTimeout(() => {
            this.speakCurrentQuestion();
          }, 300);
        });
      } else {
        this.compileFinalReport();
      }
    },

    async compileFinalReport() {
      const token = localStorage.getItem('saas_token');
      try {
        const payload = {
          session_id: this.interviewSessionId,
          target_role: this.interviewTargetRole,
          interview_type: this.interviewType,
          evaluations: this.sessionEvaluations
        };

        const res = await fetch('/api/interview/final-report', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            ...(token ? { 'Authorization': `Bearer ${token}` } : {})
          },
          body: JSON.stringify(payload)
        });

        if (!res.ok) throw new Error(`HTTP ${res.status}`);

        const repData = await res.json();
        this.finalReport = repData;
        this.interviewStep = 'final_report';

        this.$nextTick(() => {
          if (window.lucide) window.lucide.createIcons();
        });

      } catch (err) {
        console.error('Failed to compile final report:', err);
        alert('Could not compile report. Returning to workspace.');
        this.closeVoiceInterviewModal();
      }
    },

    // ═══════════════════════════════════════════════════════════════════
    // REAL-TIME AI VIDEO CONFERENCE & LIVE MISTAKE COACHING METHODS
    // ═══════════════════════════════════════════════════════════════════

    startRealtimeConference(role = '', company = '') {
      // Close other modals if open
      this.closeVoiceInterviewModal();
      this.showCopilotModal = false;

      this.conferenceTargetRole = role || this.tailoredData?.target_job_title || this.targetJobTitle || 'Automotive Technician';
      this.conferenceTargetCompany = company || this.targetCompany || '';
      this.conferenceSessionId = 'conf_' + Math.random().toString(36).substring(2, 11);
      this.conferenceDurationSeconds = 0;
      this.conferenceConversationHistory = [];
      this.conferenceMistakes = [];
      this.activeCoachingNudge = null;
      this.isCameraOn = true;
      this.isMicMuted = false;
      this.isAiSpeakingTurn = false;
      this.isCandidateSpeaking = false;
      this.liveSubtitleSpeaker = '';
      this.liveSubtitleText = '';
      this.conferenceSidebarOpen = false;
      this.realtimeConferenceOpen = true;

      // Start meeting duration timer
      if (this.conferenceTimerInterval) clearInterval(this.conferenceTimerInterval);
      this.conferenceTimerInterval = setInterval(() => {
        this.conferenceDurationSeconds++;
      }, 1000);

      // Initialize candidate webcam feed
      if (navigator.mediaDevices && navigator.mediaDevices.getUserMedia) {
        navigator.mediaDevices.getUserMedia({ video: true, audio: true })
          .then(stream => {
            this.candidateStream = stream;
            this.$nextTick(() => {
              const vid = document.getElementById('candidate-webcam-video');
              if (vid) {
                vid.srcObject = stream;
              }
            });
          })
          .catch(err => {
            console.warn('Camera/mic access unavailable or denied:', err);
            this.isCameraOn = false;
          });
      }

      this.$nextTick(() => {
        if (window.lucide) window.lucide.createIcons();

        // AI Interviewer opening line in conference
        const welcomeText = `Hello! Welcome to our live technical conference for the ${this.conferenceTargetRole} role. Can you introduce yourself and walk me through your core background and hands-on diagnostic experience?`;
        
        setTimeout(() => {
          this.conferenceConversationHistory.push({
            speaker: 'interviewer',
            text: welcomeText,
            timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
          });
          this.speakAiConferenceResponse(welcomeText, () => {
            this.initCandidateConferenceSpeechRecognition();
          });
        }, 500);
      });
    },

    speakAiConferenceResponse(text, onComplete) {
      if (!window.speechSynthesis) {
        if (onComplete) onComplete();
        return;
      }

      window.speechSynthesis.cancel();
      this.isAiThinking = false;
      this.isAiSpeakingTurn = true;
      this.liveSubtitleSpeaker = 'Alex (Interviewer)';
      this.liveSubtitleText = text;

      const utterance = new SpeechSynthesisUtterance(text);
      utterance.rate = 0.95;
      utterance.pitch = 1.0;

      const voices = window.speechSynthesis.getVoices();
      const naturalVoice = voices.find(v => v.lang.startsWith('en') && (v.name.includes('Natural') || v.name.includes('Google') || v.name.includes('Daniel') || v.name.includes('Samantha')));
      if (naturalVoice) utterance.voice = naturalVoice;

      utterance.onend = () => {
        this.isAiSpeakingTurn = false;
        if (onComplete) onComplete();
      };
      utterance.onerror = () => {
        this.isAiSpeakingTurn = false;
        if (onComplete) onComplete();
      };

      window.speechSynthesis.speak(utterance);
    },

    initCandidateConferenceSpeechRecognition() {
      if (this.isMicMuted || !this.realtimeConferenceOpen) return;

      const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
      if (!SpeechRecognition) {
        this.activeCoachingNudge = "💡 Speech recognition unavailable in this browser. Please use Chrome or Edge for full live voice conference.";
        return;
      }

      try {
        if (!this.conferenceSpeechRecognition) {
          const rec = new SpeechRecognition();
          rec.continuous = false; // Turn-based listening
          rec.interimResults = true;
          rec.lang = 'en-US';

          let turnTranscript = '';
          let turnStartTime = Date.now();

          rec.onstart = () => {
            this.isCandidateSpeaking = true;
            turnStartTime = Date.now();
            turnTranscript = '';
          };

          rec.onresult = (event) => {
            let interim = '';
            for (let i = event.resultIndex; i < event.results.length; ++i) {
              if (event.results[i].isFinal) {
                turnTranscript += ' ' + event.results[i][0].transcript.trim();
              } else {
                interim += event.results[i][0].transcript;
              }
            }
            const currentFull = (turnTranscript + ' ' + interim).trim();
            if (currentFull) {
              this.isCandidateSpeaking = true;
              this.liveSubtitleSpeaker = 'You (Candidate)';
              this.liveSubtitleText = currentFull;

              // Ultra-Low Latency Auto-Silence Trigger:
              // If candidate pauses for 1200ms after speaking at least 3 words, stop recognition immediately
              if (this.conferenceSilenceTimer) clearTimeout(this.conferenceSilenceTimer);
              if (currentFull.split(/\s+/).length >= 3) {
                this.conferenceSilenceTimer = setTimeout(() => {
                  try {
                    rec.stop();
                  } catch (e) {}
                }, 1200);
              }
            }
          };

          rec.onerror = (e) => {
            if (e.error === 'no-speech') {
              return; // Natural pause between conversational speech turns
            }
            console.warn('Conference speech recognition error:', e.error);
            this.isCandidateSpeaking = false;
            if (this.conferenceSilenceTimer) clearTimeout(this.conferenceSilenceTimer);
          };

          rec.onend = () => {
            this.isCandidateSpeaking = false;
            if (this.conferenceSilenceTimer) {
              clearTimeout(this.conferenceSilenceTimer);
              this.conferenceSilenceTimer = null;
            }
            const finalClean = turnTranscript.trim();
            const durationSec = Math.max(3, Math.round((Date.now() - turnStartTime) / 1000));

            if (finalClean && finalClean.split(/\s+/).length >= 2 && !this.isMicMuted && this.realtimeConferenceOpen) {
              this.handleCandidateSpokenTurn(finalClean, durationSec);
            } else if (this.realtimeConferenceOpen && !this.isAiSpeakingTurn && !this.isAiThinking && !this.isMicMuted) {
              // Restart listening if nothing substantial was spoken
              setTimeout(() => {
                try { rec.start(); } catch (err) {}
              }, 300);
            }
          };

          this.conferenceSpeechRecognition = rec;
        }

        if (!this.isAiSpeakingTurn && !this.isAiThinking && !this.isMicMuted) {
          this.conferenceSpeechRecognition.start();
        }

      } catch (err) {
        console.warn('Error starting conference speech recognition:', err);
      }
    },

    forceFinishCandidateSpeaking() {
      if (this.conferenceSilenceTimer) {
        clearTimeout(this.conferenceSilenceTimer);
        this.conferenceSilenceTimer = null;
      }
      if (this.conferenceSpeechRecognition) {
        try {
          this.conferenceSpeechRecognition.stop();
        } catch (e) {}
      }
    },

    async handleCandidateSpokenTurn(candidateSpeech, durationSec) {
      if (this.conferenceSilenceTimer) {
        clearTimeout(this.conferenceSilenceTimer);
        this.conferenceSilenceTimer = null;
      }
      this.isAiThinking = true;
      this.liveSubtitleSpeaker = 'Alex (Interviewer)';
      this.liveSubtitleText = '🤔 Alex is analyzing your response...';
      const token = localStorage.getItem('saas_token');

      try {
        const payload = {
          session_id: this.conferenceSessionId,
          candidate_transcript: candidateSpeech,
          conversation_history: this.conferenceConversationHistory,
          target_role: this.conferenceTargetRole,
          target_company: this.conferenceTargetCompany || null,
          speaking_duration_seconds: durationSec
        };

        const res = await fetch('/api/conference/turn', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            ...(token ? { 'Authorization': `Bearer ${token}` } : {})
          },
          body: JSON.stringify(payload)
        });

        if (!res.ok) throw new Error(`Turn HTTP ${res.status}`);

        const data = await res.json();

        // Record turn in history with mistakes attached
        this.conferenceConversationHistory.push({
          speaker: 'candidate',
          text: candidateSpeech,
          mistakes: data.mistakes_detected || [],
          timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
        });

        // Add to aggregate mistakes list for debrief
        if (data.mistakes_detected && data.mistakes_detected.length > 0) {
          this.conferenceMistakes.push(...data.mistakes_detected);
        }

        // Display live floating HUD coaching alert ("Waradi Kiyala Denna")
        if (data.live_coaching_nudge) {
          this.activeCoachingNudge = data.live_coaching_nudge;
          setTimeout(() => {
            if (this.activeCoachingNudge === data.live_coaching_nudge) {
              this.activeCoachingNudge = null;
            }
          }, 6000);
        }

        // Add interviewer reply to history
        this.conferenceConversationHistory.push({
          speaker: 'interviewer',
          text: data.interviewer_reply,
          timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
        });

        this.$nextTick(() => {
          if (window.lucide) window.lucide.createIcons();
        });

        // Speak interviewer response aloud, then resume listening
        this.speakAiConferenceResponse(data.interviewer_reply, () => {
          if (data.is_interview_complete) {
            this.endRealtimeConference();
          } else {
            setTimeout(() => {
              this.initCandidateConferenceSpeechRecognition();
            }, 300);
          }
        });

      } catch (err) {
        console.error('Conference turn exchange failed:', err);
        setTimeout(() => {
          this.initCandidateConferenceSpeechRecognition();
        }, 800);
      }
    },

    toggleConferenceMic() {
      this.isMicMuted = !this.isMicMuted;
      if (this.candidateStream) {
        this.candidateStream.getAudioTracks().forEach(track => {
          track.enabled = !this.isMicMuted;
        });
      }
      if (this.isMicMuted && this.conferenceSpeechRecognition) {
        try { this.conferenceSpeechRecognition.stop(); } catch (e) {}
      } else if (!this.isMicMuted && !this.isAiSpeakingTurn) {
        this.initCandidateConferenceSpeechRecognition();
      }
    },

    toggleConferenceCamera() {
      this.isCameraOn = !this.isCameraOn;
      if (this.candidateStream) {
        this.candidateStream.getVideoTracks().forEach(track => {
          track.enabled = this.isCameraOn;
        });
      }
    },

    formatConferenceDuration(sec) {
      const mins = Math.floor(sec / 60);
      const s = sec % 60;
      return `${mins.toString().padStart(2, '0')}:${s.toString().padStart(2, '0')}`;
    },

    async endRealtimeConference() {
      // 1. Stop webcam and mic streams
      if (this.candidateStream) {
        this.candidateStream.getTracks().forEach(track => track.stop());
        this.candidateStream = null;
      }

      // 2. Stop timers and recognition
      if (this.conferenceTimerInterval) {
        clearInterval(this.conferenceTimerInterval);
        this.conferenceTimerInterval = null;
      }

      if (this.conferenceSpeechRecognition) {
        try { this.conferenceSpeechRecognition.stop(); } catch (e) {}
        this.conferenceSpeechRecognition = null;
      }

      if (window.speechSynthesis) {
        window.speechSynthesis.cancel();
      }

      this.isAiSpeakingTurn = false;
      this.isCandidateSpeaking = false;
      this.realtimeConferenceOpen = false;

      // 3. Compile executive post-conference debrief
      const token = localStorage.getItem('saas_token');
      try {
        const payload = {
          session_id: this.conferenceSessionId,
          target_role: this.conferenceTargetRole,
          target_company: this.conferenceTargetCompany || null,
          turns_history: this.conferenceConversationHistory,
          all_mistakes: this.conferenceMistakes
        };

        const res = await fetch('/api/conference/debrief', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            ...(token ? { 'Authorization': `Bearer ${token}` } : {})
          },
          body: JSON.stringify(payload)
        });

        if (res.ok) {
          const debrief = await res.json();
          this.conferenceDebriefData = debrief;
          this.conferenceDebriefModalOpen = true;
          this.$nextTick(() => {
            if (window.lucide) window.lucide.createIcons();
          });
        }
      } catch (err) {
        console.error('Failed to generate conference debrief:', err);
      }
    }
  };
}


