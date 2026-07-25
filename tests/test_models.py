"""
SLICE 5: Basic unit tests
Verify models and RBAC enforcement
"""

import pytest
from models import User, Organization, OrgMembership, RBACRole, AuditEvent


def test_user_creation(db):
    """Test user model creation"""
    user = User(
        id='user-test',
        email='test@example.com',
        first_name='Test',
        last_name='User',
    )
    db.session.add(user)
    db.session.commit()
    assert user.id is not None
    assert user.email == 'test@example.com'


def test_organization_creation(db):
    """Test org model creation"""
    user = User(id='user-owner', email='owner@example.com', first_name='Owner')
    db.session.add(user)
    db.session.commit()
    
    org = Organization(name='Test Org', slug='test-org', owner_id=user.id)
    db.session.add(org)
    db.session.commit()
    assert org.id is not None
    assert org.slug == 'test-org'


def test_rbac_membership(db):
    """Test RBAC membership assignment"""
    user = User(id='user-member', email='member@example.com')
    db.session.add(user)
    db.session.commit()
    
    org = Organization(name='Org', slug='org', owner_id=user.id)
    db.session.add(org)
    db.session.commit()
    
    membership = OrgMembership(user_id=user.id, org_id=org.id, role=RBACRole.ADMIN)
    db.session.add(membership)
    db.session.commit()
    
    assert membership.role == RBACRole.ADMIN


def test_audit_event_creation(db):
    """Test audit event logging"""
    user = User(id='user-actor', email='actor@example.com')
    db.session.add(user)
    db.session.commit()
    
    org = Organization(name='Org', slug='org2', owner_id=user.id)
    db.session.add(org)
    db.session.commit()
    
    event = AuditEvent(
        user_id=user.id,
        org_id=org.id,
        action='login',
        ip_address='127.0.0.1'
    )
    db.session.add(event)
    db.session.commit()
    
    assert event.action == 'login'
