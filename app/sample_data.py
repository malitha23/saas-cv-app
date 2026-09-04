"""High-quality sample resumes and job descriptions for instant testing and demo."""

SAMPLE_RESUMES = {
    "software_engineer": {
        "title": "Senior Software Engineer (Full Stack)",
        "name": "Alex Chen",
        "email": "alex.chen.dev@gmail.com",
        "phone": "+1 (415) 555-0192",
        "location": "San Francisco, CA",
        "linkedin": "linkedin.com/in/alexchen-dev",
        "github": "github.com/alexchen-cloud",
        "raw_text": """ALEX CHEN
San Francisco, CA | (415) 555-0192 | alex.chen.dev@gmail.com
LinkedIn: linkedin.com/in/alexchen-dev | GitHub: github.com/alexchen-cloud

PROFESSIONAL SUMMARY
Full Stack Software Engineer with 6+ years of experience designing, scaling, and maintaining distributed microservices and modern web applications. Proficient in Python, TypeScript, React, PostgreSQL, Docker, and AWS. Proven track record reducing API latency by 45% and leading engineering teams to deliver high-availability FinTech platforms.

TECHNICAL SKILLS
Languages: Python, TypeScript, JavaScript, Go, SQL, HTML5/CSS3
Frameworks & Libraries: FastAPI, Django, React, Next.js, Node.js, Express, Tailwind CSS
Cloud & DevOps: AWS (EC2, S3, RDS, Lambda), Docker, Kubernetes, CI/CD (GitHub Actions), Terraform
Databases: PostgreSQL, Redis, MongoDB, DynamoDB
Tools & Methodologies: Git, RESTful APIs, GraphQL, Microservices, Agile/Scrum, Test-Driven Development (TDD)

WORK EXPERIENCE

Senior Software Engineer | Apex Financial Technologies | San Francisco, CA
March 2022 - Present
- Architected and deployed a real-time transaction processing pipeline in Python and FastAPI handling 15M+ daily API requests with 99.99% uptime.
- Reduced p99 database query latency by 48% through Redis distributed caching and PostgreSQL indexing strategies.
- Spearheaded migration from monolithic Ruby service to modular event-driven microservices architecture using AWS SQS and Docker.
- Mentored 5 junior and mid-level engineers in clean code principles, automated integration testing, and code review standards.
- Implemented OAuth2 and JWT token authentication standards ensuring SOC 2 and PCI-DSS compliance across all endpoints.

Software Engineer | Nova Retail Cloud | San Jose, CA
July 2019 - February 2022
- Developed high-conversion customer checkout web applications using React, TypeScript, and Redux Toolkit, lifting mobile conversion by 18%.
- Built automated inventory synchronization backend services integrating with Shopify and Stripe APIs.
- Established end-to-end CI/CD deployment pipelines using GitHub Actions, cutting release deployment cycle times from 2 days to 15 minutes.
- Authored comprehensive unit and integration test suites using PyTest and Jest achieving 88% overall code coverage.

EDUCATION
Bachelor of Science in Computer Science | University of California, Berkeley
Graduation: May 2019 | GPA: 3.8/4.0

PROJECTS
CloudScale API Gateway: Open-source rate-limiting and reverse proxy gateway built with Go, Redis, and Docker. 1.2k+ GitHub stars.
AI Resume Optimizer: Python FastAPI and React application providing automated ATS resume analysis and semantic keyword matching.

CERTIFICATIONS
AWS Certified Solutions Architect – Associate (2023)
""",
        "job_description": """Company: Stripe / FinTech Unicorn
Role: Senior Full Stack Engineer (Core Payments Platform)
Location: San Francisco, CA / Remote

About the Role:
We are looking for a Senior Full Stack Engineer to join our Core Payments engineering group. You will design, build, and maintain mission-critical payment ingestion services, developer APIs, and partner integration portals that process billions in global volume.

Key Responsibilities:
- Design and implement scalable, low-latency RESTful APIs and distributed microservices using Python (FastAPI/Django) and Go.
- Build intuitive, high-performance web dashboards and developer tools with React, TypeScript, and modern frontend frameworks.
- Optimize high-throughput PostgreSQL and Redis database systems for maximum resilience, reliability, and security.
- Collaborate with Product Managers, Security Engineers, and Compliance teams to maintain SOC-2 and PCI compliance standards.
- Lead technical design reviews and champion engineering best practices, CI/CD automation, and test coverage.

Requirements:
- 5+ years of software engineering experience building production-grade web applications and distributed backend systems.
- Strong proficiency in Python, TypeScript/JavaScript, and modern relational databases (PostgreSQL).
- Deep experience with cloud architecture (AWS/GCP), containerization (Docker, Kubernetes), and CI/CD pipelines.
- Demonstrated success optimizing high-throughput APIs, caching layers, and database query performance.
- Excellent communication skills and passion for mentoring engineers and fostering engineering excellence."""
    },
    
    "product_manager": {
        "title": "Senior Product Manager",
        "name": "Sarah Jenkins",
        "email": "sarah.jenkins.pm@gmail.com",
        "phone": "+1 (206) 555-0144",
        "location": "Seattle, WA",
        "linkedin": "linkedin.com/in/sarahjenkins-pm",
        "github": "",
        "raw_text": """SARAH JENKINS
Seattle, WA | (206) 555-0144 | sarah.jenkins.pm@gmail.com | linkedin.com/in/sarahjenkins-pm

PROFESSIONAL SUMMARY
Data-driven Senior Product Manager with 7+ years of experience steering enterprise SaaS products from 0-to-1 concept to multi-million ARR scale. Proven expertise in PLG (Product-Led Growth), user onboarding optimization, customer discovery, and cross-functional agile leadership. Champion of metric-driven experimentation, increasing user activation by 35% and retention by 22%.

CORE COMPETENCIES
Product Strategy & Roadmap, Customer Discovery & UX Research, Product-Led Growth (PLG), A/B Testing & Experimentation, Agile / Scrum Leadership, Data Analytics & SQL, Go-To-Market (GTM) Strategy, Monetization & Pricing.
Tools: Jira, Amplitude, Mixpanel, SQL, Figma, Postman, Segment, Tableau.

WORK EXPERIENCE

Lead Product Manager | CloudFlow Systems | Seattle, WA
January 2022 - Present
- Spearheaded product strategy for CloudFlow's self-serve enterprise tier, growing ARR from $4.2M to $11.8M in 18 months.
- Redesigned the developer onboarding funnel, cutting time-to-first-value (TTFV) from 45 minutes to 7 minutes and lifting conversion by 34%.
- Defined and tracked north-star metrics (WAU, activation rate, churn) utilizing Amplitude and SQL pipelines.
- Led a cross-functional agile squad of 10 engineers, 2 UX designers, and dedicated PMMs to ship 4 major quarterly releases on schedule.

Product Manager | Omnia SaaS Solutions | Seattle, WA
June 2018 - December 2021
- Owned the core collaboration workspace feature set used by 180,000+ daily active users.
- Designed and executed 30+ iterative A/B experiments on sign-up flow, boosting free-to-paid trial upgrade rate by 22%.
- Conducted 100+ customer interview sessions to construct voice-of-customer insights that guided product roadmaps.

EDUCATION
Master of Science in Information Management | University of Washington, 2018
Bachelor of Arts in Economics | University of Oregon, 2016
""",
        "job_description": """Company: Figma / Enterprise SaaS
Role: Senior Product Manager (Growth & Monetization)
Location: Remote / San Francisco, CA

We are seeking a Senior Product Manager to drive Growth, Self-Serve Monetization, and User Onboarding across our collaborative design ecosystem.

What You'll Do:
- Own the end-to-end self-serve growth funnel, driving user activation, conversion, and net retention.
- Drive rapid hypothesis-driven experimentation and A/B testing programs to optimize onboarding and time-to-value.
- Work closely with Engineering, Design, Data Science, and Marketing to build seamless self-serve upgrade flows.
- Define quantitative product metrics, analyze cohort behaviors in Amplitude/Mixpanel, and present data-backed product roadmaps to leadership.

Qualifications:
- 5+ years of product management experience in SaaS or PLG software companies.
- Proven track record driving revenue growth, conversion optimization, and retention.
- Strong analytical foundation with deep experience in SQL, Mixpanel/Amplitude, and experimentation platforms.
- Exceptional storytelling and cross-functional leadership skills."""
    }
}
