import os
import re
import html
import time
import logging
from datetime import datetime
from collections import defaultdict
from functools import wraps
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, session
from werkzeug.utils import secure_filename
from flask_sqlalchemy import SQLAlchemy
from werkzeug.middleware.proxy_fix import ProxyFix
from flask_compress import Compress
from profiles_data import get_profiles_by_view, get_all_profiles, PLATFORM_PRODUCTS

# ─── Rate Limiting (in-memory, per-IP) ────────────────────────────────────────
_rl_data: dict = defaultdict(list)

def rate_limit(max_calls: int = 10, period: int = 60):
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            forwarded = request.environ.get('HTTP_X_FORWARDED_FOR', request.remote_addr or '')
            ip = forwarded.split(',')[0].strip()
            key = f"{f.__name__}:{ip}"
            now = time.time()
            _rl_data[key] = [t for t in _rl_data[key] if now - t < period]
            if len(_rl_data[key]) >= max_calls:
                logging.warning(f"Rate limit hit: {key}")
                return jsonify({
                    "status": "error",
                    "message": "Too many requests. Please wait and try again."
                }), 429
            _rl_data[key].append(now)
            return f(*args, **kwargs)
        return wrapper
    return decorator


# ─── Input Sanitization ───────────────────────────────────────────────────────
_PERSONAL_DOMAINS = {
    'gmail.com', 'yahoo.com', 'hotmail.com', 'outlook.com', 'aol.com',
    'icloud.com', 'protonmail.com', 'live.com', 'msn.com', 'me.com',
    'mac.com', 'ymail.com', 'mail.com',
}

def sanitize(value, max_len: int = 500) -> str:
    if not isinstance(value, str):
        return ''
    return html.escape(re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', '', value.strip()))[:max_len]

def is_personal_email(email: str) -> bool:
    if not email or '@' not in email:
        return True
    domain = email.rsplit('@', 1)[-1].lower().strip()
    return domain in _PERSONAL_DOMAINS

# Configure logging
logging.basicConfig(level=logging.INFO)

# Create the Flask app (single instance)
app = Flask(__name__)
_session_secret = os.environ.get("SESSION_SECRET")
_is_production = (
    os.environ.get("VERCEL_ENV") == "production"
    or os.environ.get("FLASK_ENV") == "production"
)
if _is_production and not _session_secret:
    raise RuntimeError("SESSION_SECRET must be configured in production")
app.secret_key = _session_secret or os.urandom(32)
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)

# ─── Gzip Compression ─────────────────────────────────────────────────────────
Compress(app)
app.config['COMPRESS_MIMETYPES'] = [
    'text/html', 'text/css', 'application/javascript',
    'application/json', 'image/svg+xml'
]
app.config['COMPRESS_LEVEL'] = 6
app.config['COMPRESS_MIN_SIZE'] = 500

# ─── Session Security ─────────────────────────────────────────────────────────
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
app.config['SESSION_COOKIE_SECURE'] = os.environ.get('FLASK_ENV') == 'production'
app.config['PERMANENT_SESSION_LIFETIME'] = 3600

# ─── Request Size Limits ──────────────────────────────────────────────────────
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16 MB max upload

# Email Configuration
from flask_mail import Mail, Message
app.config['MAIL_SERVER'] = os.environ.get('MAIL_SERVER', 'smtp.gmail.com')
app.config['MAIL_PORT'] = int(os.environ.get('MAIL_PORT', 587))
app.config['MAIL_USE_TLS'] = os.environ.get('MAIL_USE_TLS', 'true').lower() == 'true'
app.config['MAIL_USERNAME'] = os.environ.get('MAIL_USERNAME')
app.config['MAIL_PASSWORD'] = os.environ.get('MAIL_PASSWORD')
app.config['MAIL_DEFAULT_SENDER'] = os.environ.get('MAIL_USERNAME')
mail = Mail(app)

# Database configuration
database_url = os.environ.get('DATABASE_URL')
USE_DATABASE = False
db = None

if database_url:
    app.config['SQLALCHEMY_DATABASE_URI'] = database_url
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
        'pool_pre_ping': True,
        'pool_recycle': 300,
    }
    app.config['UPLOAD_FOLDER'] = 'static/uploads'
    USE_DATABASE = True
else:
    logging.warning("Database not configured - some features will be limited")

# Allowed file extensions
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'mp4', 'avi', 'mov', 'wmv', 'webm'}
ALLOWED_VIDEO_EXTENSIONS = {'mp4', 'avi', 'mov', 'wmv', 'webm'}
ALLOWED_IMAGE_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

# Initialize database models
Testimonial = ContactSubmission = NewsletterSubscriber = None
ServiceType = TestimonialStatus = VIPBoardMember = None
BoardMember = Membership = User = OAuth = None

if USE_DATABASE:
    try:
        from models import (db, Testimonial, ContactSubmission, NewsletterSubscriber,
                            ServiceType, TestimonialStatus, VIPBoardMember,
                            BoardMember, Membership, User, OAuth)
        db.init_app(app)
        with app.app_context():
            try:
                import replit_auth as replit_auth_module
                try:
                    app.register_blueprint(replit_auth_module.replit_auth_blueprint(), url_prefix="/auth")
                except AttributeError:
                    app.register_blueprint(replit_auth_module.make_replit_blueprint(), url_prefix="/auth")
            except Exception as e:
                logging.warning(f"Replit auth blueprint not registered: {e}")
            try:
                db.create_all()
                logging.info("Database tables created")
            except Exception as e:
                logging.warning(f"Database table creation failed (running without DB): {e}")
                USE_DATABASE = False
    except Exception as e:
        logging.warning(f"Database initialization failed (running without DB): {e}")
        USE_DATABASE = False
        db = None

# Import replit_auth for login decorators
try:
    import replit_auth
    REPLIT_AUTH_AVAILABLE = True
except ImportError:
    replit_auth = None
    REPLIT_AUTH_AVAILABLE = False
    logging.warning("Replit auth not available")

# Import GitHub OAuth authentication
try:
    from github_auth import github_auth
    GITHUB_AUTH_AVAILABLE = True
except ImportError:
    GITHUB_AUTH_AVAILABLE = False
    logging.warning("GitHub OAuth not available")

# Import Notion client
try:
    from notion_client import Client as NotionClient
    NOTION_LIBRARY_AVAILABLE = True
except ImportError:
    NOTION_LIBRARY_AVAILABLE = False
    NotionClient = None
    logging.warning("Notion library not available")

# Notion CMS stubs
CMS_AVAILABLE = False
notion_cms = None
content_sync = None
get_services_from_notion = lambda: []
get_news_from_notion = lambda: []
get_testimonials_from_notion = lambda: []
get_featured_content = lambda: []
create_sample_content = lambda: False
auto_sync_content = lambda: {}
get_cached_content = lambda: {}
initialize_default_content = lambda: False

# OpenAI for AI Cybersecurity Assistant
AI_AVAILABLE = False
openai_client = None
try:
    from openai import OpenAI
    api_key = os.getenv("OPENAI_API_KEY")
    if api_key:
        openai_client = OpenAI(api_key=api_key)
        AI_AVAILABLE = True
    else:
        logging.warning("OpenAI API key not configured")
except ImportError:
    logging.warning("OpenAI not available for AI assistant")

# Telegram Bot
BOT_AVAILABLE = False
telegram_bot_instance = None

# Branding Settings
SITE_NAME = os.environ.get('SITE_NAME', 'GEM Assist Enterprise')
PRIMARY_COLOR = os.environ.get('PRIMARY_COLOR', '#0066cc')
CANONICAL_SITE_URL = os.environ.get(
    'CANONICAL_SITE_URL',
    'https://www.gemcybersecurityassist.com',
).rstrip('/')
CANONICAL_CLIENT_LOGIN_URL = os.environ.get(
    'CANONICAL_CLIENT_LOGIN_URL',
    f'{CANONICAL_SITE_URL}/client-login',
)
CANONICAL_GET_STARTED_URL = os.environ.get(
    'CANONICAL_GET_STARTED_URL',
    f'{CANONICAL_SITE_URL}/get-started',
)
CANONICAL_TRUST_CENTER_URL = os.environ.get(
    'CANONICAL_TRUST_CENTER_URL',
    f'{CANONICAL_SITE_URL}/trust-center',
)
CONTACT_RECIPIENT_EMAIL = os.environ.get(
    'CONTACT_RECIPIENT_EMAIL',
    'info@gemcybersecurityassist.com',
)


def allowed_file(filename, file_type='any'):
    if file_type == 'video':
        return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_VIDEO_EXTENSIONS
    elif file_type == 'image':
        return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_IMAGE_EXTENSIONS
    else:
        return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def get_notion_team_data():
    """Fetch team member data from Notion database"""
    if not NOTION_LIBRARY_AVAILABLE or not NotionClient:
        return []
    notion_secret = os.environ.get('NOTION_INTEGRATION_SECRET')
    database_id = os.environ.get('NOTION_DATABASE_ID')
    if not notion_secret or not database_id:
        return []
    try:
        notion = NotionClient(auth=notion_secret, timeout_ms=3000)
        response = notion.databases.query(database_id=database_id)
        team_members = []
        for page in response['results']:
            properties = page['properties']
            member = {'name': '', 'position': '', 'department': '', 'email': '', 'bio': '', 'image': ''}
            for prop_name, prop_data in properties.items():
                prop_type = prop_data['type']
                if prop_type == 'title' and prop_data['title']:
                    member['name'] = prop_data['title'][0]['plain_text']
                elif prop_type == 'rich_text' and prop_data['rich_text']:
                    text_content = prop_data['rich_text'][0]['plain_text']
                    if 'position' in prop_name.lower() or 'role' in prop_name.lower():
                        member['position'] = text_content
                    elif 'department' in prop_name.lower() or 'division' in prop_name.lower():
                        member['department'] = text_content
                    elif 'email' in prop_name.lower():
                        member['email'] = text_content
                    elif 'bio' in prop_name.lower() or 'description' in prop_name.lower():
                        member['bio'] = text_content
                elif prop_type == 'select' and prop_data['select']:
                    if 'department' in prop_name.lower() or 'division' in prop_name.lower():
                        member['department'] = prop_data['select']['name']
                elif prop_type == 'files' and prop_data['files']:
                    member['image'] = prop_data['files'][0]['file']['url']
            if member['name']:
                team_members.append(member)
        return team_members
    except Exception as e:
        logging.error(f"Error fetching Notion data: {e}")
        return []


def categorize_team_members(team_members):
    """Categorize team members into cybersecurity and real estate divisions"""
    cybersecurity_team = []
    real_estate_team = []
    cybersecurity_keywords = ['cyber', 'security', 'threat', 'analyst', 'monitoring', 'compliance', 'incident', 'forensic']
    real_estate_keywords = ['real estate', 'property', 'investment', 'mortgage', 'leasing', 'portfolio', 'advisor', 'broker']
    for member in team_members:
        member_text = f"{member['position']} {member['department']} {member['bio']}".lower()
        if any(keyword in member_text for keyword in cybersecurity_keywords):
            cybersecurity_team.append(member)
        elif any(keyword in member_text for keyword in real_estate_keywords):
            real_estate_team.append(member)
        else:
            if 'manager' in member['position'].lower() or 'ceo' in member['position'].lower():
                cybersecurity_team.append(member)
            else:
                real_estate_team.append(member)
    return cybersecurity_team, real_estate_team


# ─── Context Processor ────────────────────────────────────────────────────────

@app.context_processor
def inject_site_settings():
    current_user = None
    if REPLIT_AUTH_AVAILABLE and replit_auth:
        try:
            current_user = replit_auth.current_user
        except Exception:
            pass
    return {
        'site_name': SITE_NAME,
        'primary_color': PRIMARY_COLOR,
        'user': current_user,
        'canonical_site_url': CANONICAL_SITE_URL,
        'canonical_client_login_url': CANONICAL_CLIENT_LOGIN_URL,
        'canonical_get_started_url': CANONICAL_GET_STARTED_URL,
        'canonical_trust_center_url': CANONICAL_TRUST_CENTER_URL,
    }


# ─── Health Check & Favicon ───────────────────────────────────────────────────

@app.route('/health')
def health():
    return jsonify({
        'status': 'ok',
        'version': '2.1.0',
    }), 200


@app.route('/favicon.ico')
def favicon():
    from flask import send_from_directory
    return send_from_directory('static/images', 'favicon.svg', mimetype='image/svg+xml')


@app.route('/apple-touch-icon.png')
@app.route('/apple-touch-icon-precomposed.png')
def apple_touch_icon():
    from flask import send_from_directory
    return send_from_directory('static/images', 'favicon.svg', mimetype='image/svg+xml')


# ─── GitHub OAuth Routes ──────────────────────────────────────────────────────

@app.route('/auth/github')
def github_login():
    if not GITHUB_AUTH_AVAILABLE or not github_auth.is_configured():
        flash('GitHub authentication is not configured', 'error')
        return redirect(url_for('index'))
    callback_url = url_for('github_callback', _external=True)
    auth_url, state = github_auth.get_authorize_url(callback_url)
    session['github_oauth_state'] = state
    return redirect(auth_url)


@app.route('/auth/github/callback')
def github_callback():
    if not GITHUB_AUTH_AVAILABLE or not github_auth.is_configured():
        flash('GitHub authentication is not configured', 'error')
        return redirect(url_for('index'))
    code = request.args.get('code')
    state = request.args.get('state')
    if not code or not state:
        flash('Missing authorization code or state', 'error')
        return redirect(url_for('index'))
    if state != session.get('github_oauth_state'):
        flash('Invalid state parameter - possible CSRF attack', 'error')
        return redirect(url_for('index'))
    access_token = github_auth.exchange_code_for_token(code)
    if not access_token:
        flash('Failed to obtain access token from GitHub', 'error')
        return redirect(url_for('index'))
    user_info = github_auth.get_user_info(access_token)
    if not user_info:
        flash('Failed to fetch user information from GitHub', 'error')
        return redirect(url_for('index'))
    session.pop('github_oauth_state', None)
    session['github_user'] = user_info
    session.permanent = True
    flash(f"Welcome, {user_info.get('name', user_info.get('login'))}!", 'success')
    return redirect(url_for('index'))


@app.route('/auth/logout-legacy')
def logout_v2():
    session.clear()
    flash('You have been logged out', 'info')
    return redirect(url_for('index'))


# ─── Service Pages ────────────────────────────────────────────────────────────

@app.route('/services/threat-monitoring')
def threat_monitoring():
    return render_template('services/threat-monitoring.html')


@app.route('/services/incident-response')
def incident_response():
    return render_template('services/incident-response.html')


@app.route('/services/compliance')
def compliance_route():
    return render_template('services/compliance.html')


@app.route('/services/monitoring')
def monitoring_redirect():
    return redirect(url_for('monitoring_route_unified'))


@app.route('/services/compliance-management')
def compliance_management_redirect():
    return redirect(url_for('compliance_route_unified'))


@app.route('/monitoring-threats')
def monitoring_route_unified():
    return render_template('services/threat-monitoring.html')


@app.route('/compliance-governance')
def compliance_route_unified():
    return render_template('services/compliance.html')


# ─── API Endpoints ────────────────────────────────────────────────────────────

@app.route('/api/contact', methods=['POST'])
@rate_limit(max_calls=5, period=60)
def api_contact():
    try:
        data = request.json or {}
        name = sanitize(data.get('name', ''), 100)
        email = sanitize(data.get('email', ''), 120)
        company = sanitize(data.get('company', ''), 100)
        message = sanitize(data.get('message', ''), 2000)
        if not name or not email or not message:
            return jsonify({"status": "error", "message": "Name, email, and message are required."}), 400
        if '@' not in email:
            return jsonify({"status": "error", "message": "A valid email address is required."}), 400
        if is_personal_email(email):
            return jsonify({"status": "error", "message": "Please use a valid business email address."}), 400
        logging.info(f"Contact form submission: {name} ({email}) from {company}")
        admin_msg = Message(
            subject=f"New GEM Enterprise inquiry: {company or name}",
            recipients=[CONTACT_RECIPIENT_EMAIL],
            reply_to=email,
            body=f"Name: {name}\nEmail: {email}\nCompany: {company}\n\nMessage:\n{message}",
        )
        try:
            mail.send(admin_msg)
        except Exception as mail_err:
            logging.error(f"Contact mail sending failed: {mail_err}")
            return jsonify({
                "status": "error",
                "message": "We could not confirm delivery. Please email info@gemcybersecurityassist.com.",
            }), 503
        return jsonify({"status": "success", "message": "Message received. Our team will contact you shortly."}), 200
    except Exception as e:
        logging.error(f"Contact API error: {e}")
        return jsonify({"status": "error", "message": "An error occurred. Please try again."}), 500


@app.route('/api/assessment', methods=['POST'])
@rate_limit(max_calls=3, period=60)
def api_assessment():
    try:
        data = request.json or {}
        name = sanitize(data.get('name', ''), 100)
        email = sanitize(data.get('email', ''), 120)
        company = sanitize(data.get('company', ''), 100)
        phone = sanitize(data.get('phone', 'N/A'), 30)
        service = sanitize(data.get('service', ''), 100)
        message = sanitize(data.get('message', ''), 2000)
        if not name or not email:
            return jsonify({"status": "error", "message": "Name and email are required."}), 400
        if '@' not in email:
            return jsonify({"status": "error", "message": "A valid email address is required."}), 400
        if is_personal_email(email):
            return jsonify({"status": "error", "message": "Please use a valid business email address."}), 400
        logging.info(f"Assessment booking: {name} ({email}) — {company}")
        admin_msg = Message(
            subject=f"New Security Assessment Request: {company}",
            recipients=[CONTACT_RECIPIENT_EMAIL],
            reply_to=email,
            body=f"Name: {name}\nEmail: {email}\nCompany: {company}\nPhone: {phone}\nService: {service}\n\nMessage:\n{message}"
        )
        user_msg = Message(
            subject="Security Assessment Request Received - GEM Cyber",
            recipients=[email],
            body=f"Hello {name},\n\nThank you for requesting a security assessment. Our team has received your request and will follow up after reviewing your eligibility and requirements.\n\nBest regards,\nGEM Cyber Security Team"
        )
        try:
            mail.send(admin_msg)
            mail.send(user_msg)
        except Exception as mail_err:
            logging.error(f"Mail sending failed: {mail_err}")
            return jsonify({
                "status": "error",
                "message": "We could not confirm delivery. Please use the application page on gemcybersecurityassist.com.",
                "application_url": CANONICAL_GET_STARTED_URL,
            }), 503
        return jsonify({
            "status": "success",
            "message": "Assessment request received. Our team will review your eligibility and requirements.",
        }), 200
    except Exception as e:
        logging.error(f"Assessment API error: {e}")
        return jsonify({"status": "error", "message": "An error occurred. Please try again."}), 500


@app.route('/api/newsletter', methods=['POST'])
@rate_limit(max_calls=3, period=300)
def api_newsletter():
    try:
        data = request.json or {}
        email = sanitize(data.get('email', ''), 120)
        if not email or '@' not in email or len(email) < 5:
            return jsonify({"status": "error", "message": "A valid email address is required."}), 400
        logging.info(f"Newsletter signup: {email}")
        msg = Message(
            subject="GEM Intelligence - Newsletter Subscription Confirmed",
            recipients=[email],
            body="Thank you for subscribing to GEM Intelligence reports. You will now receive our latest cybersecurity threat reports and market insights."
        )
        try:
            mail.send(msg)
        except Exception as mail_err:
            logging.error(f"Newsletter mail failed: {mail_err}")
            return jsonify({
                "status": "error",
                "message": "We could not confirm your subscription. Please try again later.",
            }), 503
        return jsonify({"status": "success", "message": "Successfully subscribed to GEM Intelligence reports."}), 200
    except Exception as e:
        logging.error(f"Newsletter API error: {e}")
        return jsonify({"status": "error", "message": "An error occurred. Please try again."}), 500


@app.route('/api/notion/cached-content')
def notion_cached_content_api():
    try:
        if CMS_AVAILABLE:
            content = get_cached_content()
            if content:
                return jsonify(content)
        import json
        with open('static/cache/notion_content.json', 'r') as f:
            return jsonify(json.load(f))
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 404


@app.route('/api/news')
def get_daily_news():
    news_data = [
        {
            "id": 1,
            "title": "Gartner Warnings: Organizations urged to block 'Agentic' AI Browsers immediately",
            "source": "TechNewsWorld",
            "time": "2h ago",
            "category": "Cybersecurity",
            "excerpt": "New report highlights critical security risks as AI-driven browsers can expose sensitive enterprise data via unauthorized exfiltration."
        },
        {
            "id": 2,
            "title": "Nvidia vs. Spectral: The $5 Trillion Battle for Compute Supremacy",
            "source": "Silicon Valley Journal",
            "time": "4h ago",
            "category": "Tech",
            "excerpt": "New compiler technology could open the door to broader hardware adoption in AI training, challenging existing silicon monopolies."
        }
    ]
    return jsonify(news_data)


# ─── Legal Pages ──────────────────────────────────────────────────────────────

@app.route('/legal/cookie-policy')
def cookie_policy():
    return render_template('legal/cookies.html')


@app.route('/legal/privacy-policy')
def privacy_policy():
    return render_template('legal/privacy.html')


@app.route('/legal/terms-of-service')
def terms_of_service():
    return render_template('legal/terms.html')


@app.route('/cookie-policy')
def cookie_policy_legacy():
    return redirect(url_for('cookie_policy'))


@app.route('/privacy-policy')
def privacy_policy_legacy():
    return redirect(url_for('privacy_policy'))


@app.route('/terms-of-service')
def terms_of_service_legacy():
    return redirect(url_for('terms_of_service'))


@app.route('/legal/privacy-policy-legacy')
def privacy_policy_v2():
    return render_template('legal/privacy.html')


@app.route('/legal/terms-of-service-legacy')
def terms_of_service_v2():
    return render_template('legal/terms.html')


@app.route('/legal/cookie-policy-legacy')
def cookie_policy_v2():
    return render_template('legal/cookies.html')


# ─── Core Pages ───────────────────────────────────────────────────────────────

@app.route('/')
def index():
    current_user = None
    if REPLIT_AUTH_AVAILABLE and replit_auth:
        try:
            current_user = replit_auth.current_user
        except Exception:
            pass
    return render_template('index.html', user=current_user)


@app.route('/dashboard')
def dashboard():
    return redirect(CANONICAL_CLIENT_LOGIN_URL, code=302)


@app.route('/bridge/alliance-trust')
@app.route('/alliance-trust')
@app.route('/alliance')
@app.route('/bridge-alliance')
def bridge_alliance():
    return render_template('bridge_alliance.html')


@app.route('/bridge/gem-cybersecurity')
@app.route('/bridge-gem')
def bridge_gem():
    return render_template('bridge_gem.html')


@app.route('/client')
@app.route('/client-portal')
def client_portal():
    return redirect(CANONICAL_CLIENT_LOGIN_URL, code=302)


@app.route('/get-started')
def get_started():
    return redirect(CANONICAL_GET_STARTED_URL, code=302)


@app.route('/about-us')
def about_page():
    return render_template('about.html')


@app.route('/about')
def about_redirect():
    return redirect(url_for('about_page'))


@app.route('/contact-us')
def contact_page():
    return render_template('contact.html')


@app.route('/contact')
def contact():
    return redirect(url_for('contact_page'))


@app.route('/services-overview')
def services_page():
    return render_template('services.html')


@app.route('/services')
def services():
    return redirect(url_for('services_page'))


@app.route('/news')
def news_feed():
    notion_services = []
    if CMS_AVAILABLE:
        cached = get_cached_content()
        notion_services = cached.get('services', [])
        if not notion_services:
            content = auto_sync_content()
            notion_services = content.get('services', [])
    return render_template('news.html', notion_services=notion_services)


@app.route('/telegram-bot-automation')
def telegram_bot():
    return render_template('telegram.html')


@app.route('/monitoring')
@app.route('/threat-monitoring-portal')
def monitoring():
    return redirect(url_for('monitoring_route_unified'))


@app.route('/teams')
def teams_page():
    return render_template('teams.html',
        executive_profiles=get_profiles_by_view('executive_board'),
        cyber_profiles=get_profiles_by_view('cybersecurity_team'),
        realty_profiles=get_profiles_by_view('partners'),
        agent_profiles=get_profiles_by_view('agent_network'),
        all_profiles=get_all_profiles(),
    )


@app.route('/leadership')
@app.route('/leadership-board')
def leadership():
    return render_template('leadership.html',
        executive_profiles=get_profiles_by_view('executive_board'),
        cyber_profiles=get_profiles_by_view('cybersecurity_team'),
    )


@app.route('/trust-compliance')
def trust_compliance():
    return render_template('trust_compliance.html')


@app.route('/portfolio')
def portfolio():
    return render_template('portfolio.html')


@app.route('/cyber-sentinel-trust')
def sentinel_trust():
    return render_template('sentinel_trust.html')


@app.route('/power-of-attorney')
def power_of_attorney():
    return render_template('power-of-attorney.html')


@app.route('/market-insights')
def market_insights():
    return render_template('market_insights.html')


@app.route('/case-studies')
def case_studies():
    return render_template('case_studies.html')


@app.route('/resources')
def resources():
    return render_template('resources.html')


@app.route('/qfs')
def qfs_route():
    return render_template('qfs.html')


@app.route('/membership')
def membership():
    membership_tiers = {
        'standard': {
            'name': 'Standard',
            'price': '$99/mo',
            'description': 'Essential security monitoring and real estate advisory access.',
            'features': [
                '24/7 threat monitoring alerts',
                'Monthly security report',
                'Real estate market insights',
                'Email support',
            ],
            'color': 'info',
            'icon': 'shield',
        },
        'professional': {
            'name': 'Professional',
            'price': '$299/mo',
            'description': 'Advanced SOC services with priority response and investment tools.',
            'features': [
                'Everything in Standard',
                'Priority incident response (4h SLA)',
                'Compliance dashboard access',
                'Portfolio management tools',
                'Dedicated account manager',
            ],
            'color': 'primary',
            'icon': 'shield-check',
            'recommended': True,
        },
        'enterprise': {
            'name': 'Enterprise',
            'price': 'Custom',
            'description': 'Full-service cybersecurity and real estate advisory for large organizations.',
            'features': [
                'Everything in Professional',
                'On-site security assessments',
                'Power of attorney services',
                'Federal compliance management',
                'White-glove onboarding',
                '24/7 dedicated hotline',
            ],
            'color': 'warning',
            'icon': 'crown',
        },
    }
    return render_template('membership.html', membership_tiers=membership_tiers)


@app.route('/submit-testimonial')
def submit_testimonial():
    return redirect(url_for('contact_page'))


@app.route('/apply-membership')
def apply_membership():
    return render_template('apply_membership.html')


@app.route('/telegram/webhook', methods=['POST'])
def telegram_webhook():
    if not BOT_AVAILABLE:
        return jsonify({'error': 'Bot handler not available'}), 503
    try:
        update = request.get_json()
        result = telegram_bot_instance.process_update(update)
        return jsonify(result), 200
    except Exception as e:
        logging.error(f"Telegram webhook error: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/monitoring-legacy-check')
def monitoring_legacy():
    return redirect(url_for('monitoring_route_unified'))


@app.route('/real-estate-testimonials')
def testimonials_route():
    notion_testimonials = []
    if CMS_AVAILABLE:
        cached = get_cached_content()
        notion_testimonials = cached.get('testimonials', [])
    featured_testimonials = [t for t in notion_testimonials if t.get('featured')] if notion_testimonials else []
    return render_template('testimonials.html',
                           notion_testimonials=notion_testimonials,
                           featured_testimonials=featured_testimonials)


@app.route('/vip-board-members')
def vip_board():
    return render_template('vip_board.html',
        vip_profiles=get_profiles_by_view('executive_board'),
        function_profiles=get_profiles_by_view('vip_visibility'),
    )


@app.route('/service/<slug>')
def service_detail(slug):
    if CMS_AVAILABLE and content_sync:
        service = content_sync.get_service_by_slug(slug)
        if service:
            return render_template('notion_content_display.html', content=service)
    return render_template('index.html'), 404


@app.route('/ai-assistant')
def ai_assistant():
    return render_template('ai_assistant.html')


@app.route('/chat', methods=['POST'])
def chat():
    if not AI_AVAILABLE or not openai_client:
        return jsonify({"reply": "AI assistant is not available."}), 503
    data = request.json
    user_message = data.get("message", "")
    try:
        completion = openai_client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "You are GEM AI Cybersecurity Assistant, an expert security advisor for GEM Assist Enterprise."},
                {"role": "user", "content": user_message}
            ]
        )
        return jsonify({"reply": completion.choices[0].message.content})
    except Exception as e:
        return jsonify({"reply": f"Error: {str(e)}"}), 500


@app.route('/incident-recovery')
def recovery_service():
    return render_template('recovery-handbook.html')


# ─── Missing Route Aliases ────────────────────────────────────────────────────

@app.route('/cybersecurity')
def cybersecurity_redirect():
    return redirect(url_for('bridge_gem'))


@app.route('/vip-board')
def vip_board_redirect():
    return redirect(url_for('vip_board'))


@app.route('/real-estate')
def real_estate_redirect():
    return redirect(url_for('bridge_alliance'))


@app.route('/legal')
def legal_hub():
    return redirect(url_for('privacy_policy'))


@app.route('/threat-assessment')
def threat_assessment():
    return redirect(url_for('monitoring_route_unified'))


@app.route('/partners')
@app.route('/partners-trustees')
def partners_trustees():
    return render_template('partners.html',
        partner_profiles=get_profiles_by_view('partners'),
        platform_products=PLATFORM_PRODUCTS,
    )


@app.route('/asset-recovery')
def asset_recovery():
    return redirect(url_for('recovery_service'))


@app.route('/digital-forensics')
def digital_forensics():
    return redirect(url_for('monitoring_route_unified'))


@app.route('/api/submit-contact', methods=['POST'])
def submit_contact_alias():
    return redirect(url_for('api_contact'), code=307)


# ─── SEO: Sitemap & Robots ────────────────────────────────────────────────────

@app.route('/sitemap.xml')
def sitemap():
    from flask import Response
    pages = [
        '/', '/about-us', '/contact-us', '/services', '/membership',
        '/real-estate', '/alliance', '/news', '/teams', '/cybersecurity',
        '/monitoring-threats', '/trust-compliance', '/power-of-attorney',
        '/market-insights', '/case-studies', '/resources',
        '/real-estate-testimonials', '/vip-board-members',
        '/ai-assistant', '/telegram-bot-automation', '/qfs',
        '/legal/privacy-policy', '/legal/terms-of-service', '/legal/cookie-policy',
    ]
    base = request.url_root.rstrip('/')
    urls = '\n'.join(
        f'  <url><loc>{base}{p}</loc><changefreq>weekly</changefreq><priority>0.8</priority></url>'
        for p in pages
    )
    xml = f'<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n{urls}\n</urlset>'
    return Response(xml, mimetype='application/xml')


@app.route('/robots.txt')
def robots():
    from flask import Response
    content = (
        "User-agent: *\n"
        "Allow: /\n"
        "Disallow: /dashboard\n"
        "Disallow: /auth/\n"
        "Disallow: /api/\n"
        "Disallow: /telegram/\n"
        f"Sitemap: {request.url_root}sitemap.xml\n"
    )
    return Response(content, mimetype='text/plain')


# ─── Security Headers ─────────────────────────────────────────────────────────

@app.after_request
def add_security_and_cache_headers(response):
    # ── Security ──────────────────────────────────────────────────────────────
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'SAMEORIGIN'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
    response.headers['Permissions-Policy'] = 'geolocation=(), microphone=(), camera=()'

    # ── Cache headers for static assets ──────────────────────────────────────
    if request.path.startswith('/static/css/') or request.path.startswith('/static/js/'):
        response.headers['Cache-Control'] = 'public, max-age=31536000, immutable'
    elif request.path.startswith('/static/images/'):
        response.headers['Cache-Control'] = 'public, max-age=2592000'
    elif request.path.startswith('/static/'):
        response.headers['Cache-Control'] = 'public, max-age=86400'
    elif request.path in ('/health', '/sitemap.xml', '/robots.txt'):
        response.headers['Cache-Control'] = 'public, max-age=300'
    elif request.path.startswith('/api/'):
        response.headers['Cache-Control'] = 'no-store'

    # ── CSP (HTML responses only) ─────────────────────────────────────────────
    if response.content_type and 'text/html' in response.content_type:
        response.headers['Content-Security-Policy'] = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' 'unsafe-eval' "
            "https://cdn.jsdelivr.net https://unpkg.com https://cdn.tailwindcss.com "
            "https://cdnjs.cloudflare.com https://kit.fontawesome.com; "
            "style-src 'self' 'unsafe-inline' "
            "https://cdn.jsdelivr.net https://cdnjs.cloudflare.com "
            "https://cdn.tailwindcss.com https://fonts.googleapis.com; "
            "font-src 'self' https://fonts.gstatic.com https://cdnjs.cloudflare.com "
            "https://ka-f.fontawesome.com; "
            "img-src 'self' data: https:; "
            "connect-src 'self' https:; "
            "frame-src 'self' https:;"
        )
    return response


# ─── Error Handlers ───────────────────────────────────────────────────────────

@app.errorhandler(404)
def not_found_error(error):
    return render_template('index.html'), 404


@app.errorhandler(500)
def internal_error(error):
    logging.error(f"Internal server error: {error}")
    return render_template('index.html'), 500
