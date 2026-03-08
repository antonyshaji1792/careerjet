/**
 * Profile Editor - Comprehensive CRUD functionality for all profile sections
 */

// Utility function to get CSRF token
function getCSRFToken() {
    return document.querySelector('meta[name="csrf-token"]').getAttribute('content');
}

// Utility function to show toast notifications
function showToast(message, type = 'success') {
    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;
    toast.innerHTML = `
        <i class="fas fa-${type === 'success' ? 'check-circle' : 'exclamation-circle'}"></i>
        <span>${message}</span>
    `;
    document.body.appendChild(toast);

    setTimeout(() => {
        toast.classList.add('show');
    }, 100);

    setTimeout(() => {
        toast.classList.remove('show');
        setTimeout(() => toast.remove(), 300);
    }, 3000);
}

// Generic Modal Manager
class ModalManager {
    constructor() {
        this.createModalContainer();
    }

    createModalContainer() {
        if (!document.getElementById('modal-container')) {
            const container = document.createElement('div');
            container.id = 'modal-container';
            document.body.appendChild(container);
        }
    }

    show(title, content, onSave, size = 'medium') {
        const modal = document.createElement('div');
        modal.className = 'modal-overlay';
        modal.style.zIndex = '999999';
        modal.innerHTML = `
            <div class="modal-dialog modal-${size}" style="position: relative; z-index: 1000000;">
                <div class="modal-header">
                    <h3>${title}</h3>
                    <button class="modal-close" type="button">
                        <i class="fas fa-times"></i>
                    </button>
                </div>
                <div class="modal-body">
                    ${content}
                </div>
                <div class="modal-footer">
                    <button class="btn btn-outline cancel-btn" type="button">Cancel</button>
                    <button class="btn btn-primary save-btn" type="button">Save</button>
                </div>
            </div>
        `;

        const container = document.getElementById('modal-container');
        container.appendChild(modal);

        const saveBtn = modal.querySelector('.save-btn');
        const cancelBtn = modal.querySelector('.cancel-btn');
        const closeBtn = modal.querySelector('.modal-close');

        // Add event listener for save button
        saveBtn.addEventListener('click', async (e) => {
            e.preventDefault();
            e.stopPropagation();

            saveBtn.disabled = true;
            saveBtn.classList.add('loading');
            try {
                const formData = this.getFormData(modal);
                const success = await onSave(formData);
                if (success) {
                    modal.remove();
                }
            } catch (error) {
                console.error('Modal save error:', error);
                showToast('An error occurred. Please try again.', 'error');
            } finally {
                saveBtn.disabled = false;
                saveBtn.classList.remove('loading');
            }
        });

        const closeModal = (e) => {
            if (e) {
                e.preventDefault();
                e.stopPropagation();
            }
            modal.remove();
        };

        cancelBtn.addEventListener('click', closeModal);
        closeBtn.addEventListener('click', closeModal);

        // Auto-focus first input with a slight delay to ensure modal is rendered
        setTimeout(() => {
            const firstInput = modal.querySelector('input, textarea, select');
            if (firstInput) {
                firstInput.focus();
                // If it's a textarea or text input, set cursor to end
                if (firstInput.tagName === 'TEXTAREA' || (firstInput.tagName === 'INPUT' && firstInput.type === 'text')) {
                    const val = firstInput.value;
                    firstInput.value = '';
                    firstInput.value = val;
                }
            }
        }, 300);
    }

    getFormData(modal) {
        const form = modal.querySelector('form') || modal.querySelector('.modal-body');
        const formData = {};
        const inputs = form.querySelectorAll('input, textarea, select');

        inputs.forEach(input => {
            if (!input.name) return;

            if (input.type === 'checkbox') {
                formData[input.name] = input.checked;
            } else if (input.type === 'radio') {
                if (input.checked) {
                    formData[input.name] = input.value;
                }
            } else {
                formData[input.name] = input.value;
            }
        });

        return formData;
    }

    confirm(message, onConfirm) {
        const modal = document.createElement('div');
        modal.className = 'modal-overlay';
        modal.innerHTML = `
            <div class="modal-dialog modal-small">
                <div class="modal-header">
                    <h3>Confirm Action</h3>
                </div>
                <div class="modal-body">
                    <p style="font-size: 0.9375rem; color: var(--dark);">${message}</p>
                </div>
                <div class="modal-footer">
                    <button class="btn btn-outline cancel-btn">Cancel</button>
                    <button class="btn btn-primary confirm-btn" style="background: #ef4444;">Delete</button>
                </div>
            </div>
        `;

        document.getElementById('modal-container').appendChild(modal);

        // Add event listeners after modal is in DOM
        const confirmBtn = modal.querySelector('.confirm-btn');
        const cancelBtn = modal.querySelector('.cancel-btn');

        confirmBtn.addEventListener('click', async () => {
            await onConfirm();
            modal.remove();
        });

        cancelBtn.addEventListener('click', () => {
            modal.remove();
        });

    }
}

let modalManager;

// Initialize modal manager when DOM is ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
        modalManager = new ModalManager();
    });
} else {
    // DOM is already ready
    modalManager = new ModalManager();
}


// ============ PROFILE HEADLINE ============
async function editHeadline() {
    const response = await fetch('/api/profile/headline');
    const data = await response.json();
    const headline = data.data?.headline || '';

    const content = `
        <form>
            <div class="form-group">
                <label>Resume Headline *</label>
                <textarea name="headline" class="form-control" rows="3" required placeholder="e.g., PHP Developer (Core PHP, Laravel, Wordpress)">${headline}</textarea>
                <small style="color: var(--gray); font-size: 0.75rem;">It is the first thing recruiters notice in your profile. Write concisely what makes you unique.</small>
            </div>
        </form>
    `;

    modalManager.show('Edit Resume Headline', content, async (formData) => {
        const response = await fetch('/api/profile/headline', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCSRFToken()
            },
            body: JSON.stringify(formData)
        });

        const result = await response.json();
        if (result.success) {
            showToast('Headline updated successfully!');
            location.reload();
            return true;
        }
        return false;
    });
}

// ============ KEY SKILLS ============
async function addSkill() {
    const content = `
        <form>
            <div class="form-group">
                <label>Skill Name *</label>
                <input type="text" name="skill_name" class="form-control" required placeholder="e.g., JavaScript, Python, React">
            </div>
        </form>
    `;

    modalManager.show('Add Skill', content, async (formData) => {
        const response = await fetch('/api/profile/skills', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCSRFToken()
            },
            body: JSON.stringify(formData)
        });

        const result = await response.json();
        if (result.success) {
            showToast('Skill added successfully!');
            location.reload();
            return true;
        }
        return false;
    });
}

async function deleteSkill(skillId) {
    // Ensure modalManager is initialized
    if (!modalManager) {
        if (confirm('Are you sure you want to delete this skill?')) {
            const response = await fetch(`/api/profile/skills/${skillId}`, {
                method: 'DELETE',
                headers: {
                    'X-CSRFToken': getCSRFToken()
                }
            });

            const result = await response.json();
            if (result.success) {
                showToast('Skill deleted successfully!');
                location.reload();
            }
        }
        return;
    }

    modalManager.confirm('Are you sure you want to delete this skill?', async () => {
        const response = await fetch(`/api/profile/skills/${skillId}`, {
            method: 'DELETE',
            headers: {
                'X-CSRFToken': getCSRFToken()
            }
        });

        const result = await response.json();
        if (result.success) {
            showToast('Skill deleted successfully!');
            location.reload();
        }
    });
}

// ============ EMPLOYMENT ============
async function addEmployment() {
    const content = `
        <form>
            <div class="form-group">
                <label>Job Title *</label>
                <input type="text" name="job_title" class="form-control" required placeholder="e.g., Software Engineer">
            </div>
            <div class="form-group">
                <label>Company Name *</label>
                <input type="text" name="company_name" class="form-control" required placeholder="e.g., Google">
            </div>
            <div class="form-row">
                <div class="form-group">
                    <label>Employment Type</label>
                    <select name="employment_type" class="form-control">
                        <option value="Full-time">Full-time</option>
                        <option value="Part-time">Part-time</option>
                        <option value="Contract">Contract</option>
                        <option value="Internship">Internship</option>
                    </select>
                </div>
                <div class="form-group">
                    <label>
                        <input type="checkbox" name="is_current" style="width: auto; margin-right: 0.5rem;">
                        Currently working here
                    </label>
                </div>
            </div>
            <div class="form-row">
                <div class="form-group">
                    <label>Start Date *</label>
                    <input type="date" name="start_date" class="form-control" required>
                </div>
                <div class="form-group">
                    <label>End Date</label>
                    <input type="date" name="end_date" class="form-control">
                </div>
            </div>
            <div class="form-group">
                <label>
                    <input type="checkbox" name="is_serving_notice" style="width: auto; margin-right: 0.5rem;">
                    Serving Notice Period
                </label>
            </div>
            <div class="form-group">
                <label>Notice Period (days)</label>
                <input type="number" name="notice_period_days" class="form-control" placeholder="e.g., 30">
            </div>
            <div class="form-group">
                <label>Job Description</label>
                <textarea name="description" class="form-control" rows="4" placeholder="Describe your role and responsibilities"></textarea>
            </div>
            <div class="form-group">
                <label>Key Skills Used</label>
                <input type="text" name="key_skills" class="form-control" placeholder="e.g., Python, Django, PostgreSQL">
            </div>
        </form>
    `;

    modalManager.show('Add Employment', content, async (formData) => {
        const response = await fetch('/api/profile/employment', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCSRFToken()
            },
            body: JSON.stringify(formData)
        });

        const result = await response.json();
        if (result.success) {
            showToast('Employment added successfully!');
            location.reload();
            return true;
        }
        return false;
    }, 'large');
}

async function editEmployment(empId) {
    try {
        const response = await fetch('/api/profile/employment');
        const data = await response.json();
        const emp = data.data.find(e => e.id === empId);

        if (!emp) {
            alert('Employment record not found in database. This employment entry is hardcoded in the template and needs to be added to the database first.\n\nPlease use the "+ Add" button to add your employment details.');
            return;
        }

        const content = `
        <form>
            <div class="form-group">
                <label>Job Title *</label>
                <input type="text" name="job_title" class="form-control" required value="${emp.job_title}">
            </div>
            <div class="form-group">
                <label>Company Name *</label>
                <input type="text" name="company_name" class="form-control" required value="${emp.company_name}">
            </div>
            <div class="form-row">
                <div class="form-group">
                    <label>Employment Type</label>
                    <select name="employment_type" class="form-control">
                        <option value="Full-time" ${emp.employment_type === 'Full-time' ? 'selected' : ''}>Full-time</option>
                        <option value="Part-time" ${emp.employment_type === 'Part-time' ? 'selected' : ''}>Part-time</option>
                        <option value="Contract" ${emp.employment_type === 'Contract' ? 'selected' : ''}>Contract</option>
                        <option value="Internship" ${emp.employment_type === 'Internship' ? 'selected' : ''}>Internship</option>
                    </select>
                </div>
                <div class="form-group">
                    <label>
                        <input type="checkbox" name="is_current" ${emp.is_current ? 'checked' : ''} style="width: auto; margin-right: 0.5rem;">
                        Currently working here
                    </label>
                </div>
            </div>
            <div class="form-row">
                <div class="form-group">
                    <label>Start Date *</label>
                    <input type="date" name="start_date" class="form-control" required value="${emp.start_date || ''}">
                </div>
                <div class="form-group">
                    <label>End Date</label>
                    <input type="date" name="end_date" class="form-control" value="${emp.end_date || ''}">
                </div>
            </div>
            <div class="form-group">
                <label>
                    <input type="checkbox" name="is_serving_notice" ${emp.is_serving_notice ? 'checked' : ''} style="width: auto; margin-right: 0.5rem;">
                    Serving Notice Period
                </label>
            </div>
            <div class="form-group">
                <label>Notice Period (days)</label>
                <input type="number" name="notice_period_days" class="form-control" value="${emp.notice_period_days || ''}">
            </div>
            <div class="form-group">
                <label>Job Description</label>
                <textarea name="description" class="form-control" rows="4">${emp.description || ''}</textarea>
            </div>
            <div class="form-group">
                <label>Key Skills Used</label>
                <input type="text" name="key_skills" class="form-control" value="${emp.key_skills || ''}">
            </div>
        </form>
    `;

        modalManager.show('Edit Employment', content, async (formData) => {
            const response = await fetch(`/api/profile/employment/${empId}`, {
                method: 'PUT',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': getCSRFToken()
                },
                body: JSON.stringify(formData)
            });

            const result = await response.json();
            if (result.success) {
                showToast('Employment updated successfully!');
                location.reload();
                return true;
            }
            return false;
        }, 'large');
    } catch (error) {
        console.error('Error editing employment:', error);
        alert('Error loading employment data. Please try again.');
    }
}

async function deleteEmployment(empId) {
    modalManager.confirm('Are you sure you want to delete this employment record?', async () => {
        const response = await fetch(`/api/profile/employment/${empId}`, {
            method: 'DELETE',
            headers: {
                'X-CSRFToken': getCSRFToken()
            }
        });

        const result = await response.json();
        if (result.success) {
            showToast('Employment deleted successfully!');
            location.reload();
        }
    });
}

// ============ EDUCATION ============
async function addEducation() {
    const content = `
        <form>
            <div class="form-group">
                <label>Degree *</label>
                <input type="text" name="degree" class="form-control" required placeholder="e.g., B.Sc Computer Science">
            </div>
            <div class="form-group">
                <label>Institution *</label>
                <input type="text" name="institution" class="form-control" required placeholder="e.g., Stanford University">
            </div>
            <div class="form-group">
                <label>Field of Study</label>
                <input type="text" name="field_of_study" class="form-control" placeholder="e.g., Computer Science">
            </div>
            <div class="form-row">
                <div class="form-group">
                    <label>Start Year</label>
                    <input type="number" name="start_year" class="form-control" placeholder="e.g., 2015">
                </div>
                <div class="form-group">
                    <label>End Year</label>
                    <input type="number" name="end_year" class="form-control" placeholder="e.g., 2019">
                </div>
            </div>
            <div class="form-row">
                <div class="form-group">
                    <label>Grade/CGPA</label>
                    <input type="text" name="grade" class="form-control" placeholder="e.g., 3.8/4.0">
                </div>
                <div class="form-group">
                    <label>Education Type</label>
                    <select name="education_type" class="form-control">
                        <option value="Full Time">Full Time</option>
                        <option value="Part Time">Part Time</option>
                        <option value="Distance Learning">Distance Learning</option>
                    </select>
                </div>
            </div>
        </form>
    `;

    modalManager.show('Add Education', content, async (formData) => {
        const response = await fetch('/api/profile/education', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCSRFToken()
            },
            body: JSON.stringify(formData)
        });

        const result = await response.json();
        if (result.success) {
            showToast('Education added successfully!');
            location.reload();
            return true;
        }
        return false;
    });
}

async function editEducation(eduId) {
    const response = await fetch('/api/profile/education');
    const data = await response.json();
    const edu = data.data.find(e => e.id === eduId);

    if (!edu) return;

    const content = `
        <form>
            <div class="form-group">
                <label>Degree *</label>
                <input type="text" name="degree" class="form-control" required value="${edu.degree}">
            </div>
            <div class="form-group">
                <label>Institution *</label>
                <input type="text" name="institution" class="form-control" required value="${edu.institution}">
            </div>
            <div class="form-group">
                <label>Field of Study</label>
                <input type="text" name="field_of_study" class="form-control" value="${edu.field_of_study || ''}">
            </div>
            <div class="form-row">
                <div class="form-group">
                    <label>Start Year</label>
                    <input type="number" name="start_year" class="form-control" value="${edu.start_year || ''}">
                </div>
                <div class="form-group">
                    <label>End Year</label>
                    <input type="number" name="end_year" class="form-control" value="${edu.end_year || ''}">
                </div>
            </div>
            <div class="form-row">
                <div class="form-group">
                    <label>Grade/CGPA</label>
                    <input type="text" name="grade" class="form-control" value="${edu.grade || ''}">
                </div>
                <div class="form-group">
                    <label>Education Type</label>
                    <select name="education_type" class="form-control">
                        <option value="Full Time" ${edu.education_type === 'Full Time' ? 'selected' : ''}>Full Time</option>
                        <option value="Part Time" ${edu.education_type === 'Part Time' ? 'selected' : ''}>Part Time</option>
                        <option value="Distance Learning" ${edu.education_type === 'Distance Learning' ? 'selected' : ''}>Distance Learning</option>
                    </select>
                </div>
            </div>
        </form>
    `;

    modalManager.show('Edit Education', content, async (formData) => {
        const response = await fetch(`/api/profile/education/${eduId}`, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCSRFToken()
            },
            body: JSON.stringify(formData)
        });

        const result = await response.json();
        if (result.success) {
            showToast('Education updated successfully!');
            location.reload();
            return true;
        }
        return false;
    });
}

async function deleteEducation(eduId) {
    modalManager.confirm('Are you sure you want to delete this education record?', async () => {
        const response = await fetch(`/api/profile/education/${eduId}`, {
            method: 'DELETE',
            headers: {
                'X-CSRFToken': getCSRFToken()
            }
        });

        const result = await response.json();
        if (result.success) {
            showToast('Education deleted successfully!');
            location.reload();
        }
    });
}

// ============ IT SKILLS ============
async function addITSkill() {
    const content = `
        <form>
            <div class="form-group">
                <label>Skill Name *</label>
                <input type="text" name="skill_name" class="form-control" required placeholder="e.g., PHP">
            </div>
            <div class="form-group">
                <label>Version</label>
                <input type="text" name="version" class="form-control" placeholder="e.g., 8.0">
            </div>
            <div class="form-group">
                <label>Last Used Year</label>
                <input type="number" name="last_used_year" class="form-control" placeholder="e.g., 2024">
            </div>
            <div class="form-row">
                <div class="form-group">
                    <label>Experience (Years)</label>
                    <input type="number" name="experience_years" class="form-control" placeholder="e.g., 3">
                </div>
                <div class="form-group">
                    <label>Experience (Months)</label>
                    <input type="number" name="experience_months" class="form-control" placeholder="e.g., 6">
                </div>
            </div>
        </form>
    `;

    modalManager.show('Add IT Skill', content, async (formData) => {
        const response = await fetch('/api/profile/it-skills', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCSRFToken()
            },
            body: JSON.stringify(formData)
        });

        const result = await response.json();
        if (result.success) {
            showToast('IT Skill added successfully!');
            location.reload();
            return true;
        }
        return false;
    });
}

async function editITSkill(skillId) {
    const response = await fetch('/api/profile/it-skills');
    const data = await response.json();
    const skill = data.data.find(s => s.id === skillId);

    if (!skill) return;

    const content = `
        <form>
            <div class="form-group">
                <label>Skill Name *</label>
                <input type="text" name="skill_name" class="form-control" required value="${skill.skill_name}">
            </div>
            <div class="form-group">
                <label>Version</label>
                <input type="text" name="version" class="form-control" value="${skill.version || ''}">
            </div>
            <div class="form-group">
                <label>Last Used Year</label>
                <input type="number" name="last_used_year" class="form-control" value="${skill.last_used_year || ''}">
            </div>
            <div class="form-row">
                <div class="form-group">
                    <label>Experience (Years)</label>
                    <input type="number" name="experience_years" class="form-control" value="${skill.experience_years || ''}">
                </div>
                <div class="form-group">
                    <label>Experience (Months)</label>
                    <input type="number" name="experience_months" class="form-control" value="${skill.experience_months || ''}">
                </div>
            </div>
        </form>
    `;

    modalManager.show('Edit IT Skill', content, async (formData) => {
        const response = await fetch(`/api/profile/it-skills/${skillId}`, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCSRFToken()
            },
            body: JSON.stringify(formData)
        });

        const result = await response.json();
        if (result.success) {
            showToast('IT Skill updated successfully!');
            location.reload();
            return true;
        }
        return false;
    });
}

async function deleteITSkill(skillId) {
    modalManager.confirm('Are you sure you want to delete this IT skill?', async () => {
        const response = await fetch(`/api/profile/it-skills/${skillId}`, {
            method: 'DELETE',
            headers: {
                'X-CSRFToken': getCSRFToken()
            }
        });

        const result = await response.json();
        if (result.success) {
            showToast('IT Skill deleted successfully!');
            location.reload();
        }
    });
}

// ============ PROFILE SUMMARY ============
async function editSummary() {
    const response = await fetch('/api/profile/summary');
    const data = await response.json();
    const summary = data.data?.summary || '';

    const content = `
        <form>
            <div class="form-group">
                <label>Profile Summary *</label>
                <textarea name="summary" class="form-control" rows="6" required placeholder="Write a brief summary of your professional experience and skills...">${summary}</textarea>
                <small style="color: var(--gray); font-size: 0.75rem;">A good summary highlights your key achievements and expertise.</small>
            </div>
        </form>
    `;

    modalManager.show('Edit Profile Summary', content, async (formData) => {
        const response = await fetch('/api/profile/summary', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCSRFToken()
            },
            body: JSON.stringify(formData)
        });

        const result = await response.json();
        if (result.success) {
            showToast('Summary updated successfully!');
            location.reload();
            return true;
        }
        return false;
    });
}

// ============ PERSONAL DETAILS ============
async function editPersonalDetails() {
    const response = await fetch('/api/profile/personal-details');
    const data = await response.json();
    const details = data.data || {};

    const content = `
        <form>
            <div class="form-group">
                <label>Full Name</label>
                <input type="text" name="full_name" class="form-control" value="${details.full_name || ''}">
            </div>
            <div class="form-row">
                <div class="form-group">
                    <label>Gender</label>
                    <select name="gender" class="form-control">
                        <option value="">Select</option>
                        <option value="Male" ${details.gender === 'Male' ? 'selected' : ''}>Male</option>
                        <option value="Female" ${details.gender === 'Female' ? 'selected' : ''}>Female</option>
                        <option value="Other" ${details.gender === 'Other' ? 'selected' : ''}>Other</option>
                    </select>
                </div>
                <div class="form-group">
                    <label>Marital Status</label>
                    <select name="marital_status" class="form-control">
                        <option value="">Select</option>
                        <option value="Single" ${details.marital_status === 'Single' ? 'selected' : ''}>Single</option>
                        <option value="Married" ${details.marital_status === 'Married' ? 'selected' : ''}>Married</option>
                    </select>
                </div>
            </div>
            <div class="form-row">
                <div class="form-group">
                    <label>Date of Birth</label>
                    <input type="date" name="date_of_birth" class="form-control" value="${details.date_of_birth || ''}">
                </div>
                <div class="form-group">
                    <label>Category</label>
                    <select name="category" class="form-control">
                        <option value="">Select</option>
                        <option value="General" ${details.category === 'General' ? 'selected' : ''}>General</option>
                        <option value="SC" ${details.category === 'SC' ? 'selected' : ''}>SC</option>
                        <option value="ST" ${details.category === 'ST' ? 'selected' : ''}>ST</option>
                        <option value="OBC" ${details.category === 'OBC' ? 'selected' : ''}>OBC</option>
                    </select>
                </div>
            </div>
            <div class="form-group">
                <label>Work Permit Country</label>
                <input type="text" name="work_permit_country" class="form-control" value="${details.work_permit_country || ''}">
            </div>
            <div class="form-group">
                <label>Address</label>
                <textarea name="address" class="form-control" rows="2">${details.address || ''}</textarea>
            </div>
            <div class="form-row">
                <div class="form-group">
                    <label>City</label>
                    <input type="text" name="city" class="form-control" value="${details.city || ''}">
                </div>
                <div class="form-group">
                    <label>State</label>
                    <input type="text" name="state" class="form-control" value="${details.state || ''}">
                </div>
            </div>
            <div class="form-row">
                <div class="form-group">
                    <label>Country</label>
                    <input type="text" name="country" class="form-control" value="${details.country || ''}">
                </div>
                <div class="form-group">
                    <label>Pincode</label>
                    <input type="text" name="pincode" class="form-control" value="${details.pincode || ''}">
                </div>
            </div>
            <div class="form-row">
                <div class="form-group">
                    <label>Phone</label>
                    <input type="tel" name="phone" class="form-control" value="${details.phone || ''}">
                </div>
                <div class="form-group">
                    <label>Alternate Phone</label>
                    <input type="tel" name="alternate_phone" class="form-control" value="${details.alternate_phone || ''}">
                </div>
            </div>
        </form>
    `;

    modalManager.show('Edit Personal Details', content, async (formData) => {
        const response = await fetch('/api/profile/personal-details', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCSRFToken()
            },
            body: JSON.stringify(formData)
        });

        const result = await response.json();
        if (result.success) {
            showToast('Personal details updated successfully!');
            location.reload();
            return true;
        }
        return false;
    }, 'large');
}

// ============ LANGUAGES ============
async function addLanguage() {
    const content = `
        <form>
            <div class="form-group">
                <label>Language *</label>
                <input type="text" name="language_name" class="form-control" required placeholder="e.g., English">
            </div>
            <div class="form-group">
                <label>Proficiency</label>
                <select name="proficiency" class="form-control">
                    <option value="Beginner">Beginner</option>
                    <option value="Intermediate">Intermediate</option>
                    <option value="Proficient">Proficient</option>
                    <option value="Expert">Expert</option>
                </select>
            </div>
            <div class="form-group">
                <label style="display: flex; align-items: center; gap: 1rem;">
                    <input type="checkbox" name="can_read" style="width: auto;">
                    <span>Can Read</span>
                </label>
            </div>
            <div class="form-group">
                <label style="display: flex; align-items: center; gap: 1rem;">
                    <input type="checkbox" name="can_write" style="width: auto;">
                    <span>Can Write</span>
                </label>
            </div>
            <div class="form-group">
                <label style="display: flex; align-items: center; gap: 1rem;">
                    <input type="checkbox" name="can_speak" style="width: auto;">
                    <span>Can Speak</span>
                </label>
            </div>
        </form>
    `;

    modalManager.show('Add Language', content, async (formData) => {
        const response = await fetch('/api/profile/languages', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCSRFToken()
            },
            body: JSON.stringify(formData)
        });

        const result = await response.json();
        if (result.success) {
            showToast('Language added successfully!');
            location.reload();
            return true;
        }
        return false;
    });
}

async function editLanguage(langId) {
    const response = await fetch('/api/profile/languages');
    const data = await response.json();
    const lang = data.data.find(l => l.id === langId);

    if (!lang) return;

    const content = `
        <form>
            <div class="form-group">
                <label>Language *</label>
                <input type="text" name="language_name" class="form-control" required value="${lang.language_name}">
            </div>
            <div class="form-group">
                <label>Proficiency</label>
                <select name="proficiency" class="form-control">
                    <option value="Beginner" ${lang.proficiency === 'Beginner' ? 'selected' : ''}>Beginner</option>
                    <option value="Intermediate" ${lang.proficiency === 'Intermediate' ? 'selected' : ''}>Intermediate</option>
                    <option value="Proficient" ${lang.proficiency === 'Proficient' ? 'selected' : ''}>Proficient</option>
                    <option value="Expert" ${lang.proficiency === 'Expert' ? 'selected' : ''}>Expert</option>
                </select>
            </div>
            <div class="form-group">
                <label style="display: flex; align-items: center; gap: 1rem;">
                    <input type="checkbox" name="can_read" ${lang.can_read ? 'checked' : ''} style="width: auto;">
                    <span>Can Read</span>
                </label>
            </div>
            <div class="form-group">
                <label style="display: flex; align-items: center; gap: 1rem;">
                    <input type="checkbox" name="can_write" ${lang.can_write ? 'checked' : ''} style="width: auto;">
                    <span>Can Write</span>
                </label>
            </div>
            <div class="form-group">
                <label style="display: flex; align-items: center; gap: 1rem;">
                    <input type="checkbox" name="can_speak" ${lang.can_speak ? 'checked' : ''} style="width: auto;">
                    <span>Can Speak</span>
                </label>
            </div>
        </form>
    `;

    modalManager.show('Edit Language', content, async (formData) => {
        const response = await fetch(`/api/profile/languages/${langId}`, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCSRFToken()
            },
            body: JSON.stringify(formData)
        });

        const result = await response.json();
        if (result.success) {
            showToast('Language updated successfully!');
            location.reload();
            return true;
        }
        return false;
    });
}

async function deleteLanguage(langId) {
    modalManager.confirm('Are you sure you want to delete this language?', async () => {
        const response = await fetch(`/api/profile/languages/${langId}`, {
            method: 'DELETE',
            headers: {
                'X-CSRFToken': getCSRFToken()
            }
        });

        const result = await response.json();
        if (result.success) {
            showToast('Language deleted successfully!');
            location.reload();
        }
    });
}

// ============ BASIC INFO MODAL (HEADER) ============
async function openBasicInfoModal() {
    try {
        const response = await fetch('/api/profile/basic-info');
        const json = await response.json();
        const data = json.data || {};

        const content = `
            <form>
                <div class="form-group">
                    <label>Full Name</label>
                    <input type="text" name="full_name" class="form-control" value="${data.full_name || ''}" required>
                </div>
                <div class="form-row">
                    <div class="form-group">
                        <label>Current Job Title</label>
                        <input type="text" name="job_title" class="form-control" value="${data.job_title || ''}" placeholder="e.g. Senior Software Engineer">
                    </div>
                    <div class="form-group">
                        <label>Company Name</label>
                        <input type="text" name="company_name" class="form-control" value="${data.company_name || ''}" placeholder="e.g. Google">
                    </div>
                </div>
                <div class="form-row">
                    <div class="form-group">
                        <label>City</label>
                        <input type="text" name="city" class="form-control" value="${data.city || ''}" placeholder="e.g. Bangalore">
                    </div>
                    <div class="form-group">
                        <label>Country</label>
                        <input type="text" name="country" class="form-control" value="${data.country || ''}" placeholder="e.g. India">
                    </div>
                </div>
                <div class="form-row">
                    <div class="form-group">
                        <label>Phone</label>
                        <input type="text" name="phone" class="form-control" value="${data.phone || ''}" placeholder="+91 9876543210">
                    </div>
                    <div class="form-group">
                        <label>Total Experience (Years)</label>
                        <input type="number" name="total_experience" class="form-control" value="${data.total_experience || 0}" step="0.1">
                    </div>
                </div>
                <div class="form-row">
                    <div class="form-group">
                        <label>Current Salary (Annual)</label>
                        <input type="number" name="current_salary" class="form-control" value="${data.current_salary || ''}" placeholder="e.g. 1500000">
                    </div>
                    <div class="form-group">
                        <label>Notice Period (Days)</label>
                        <input type="number" name="notice_period" class="form-control" value="${data.notice_period || ''}" placeholder="e.g. 30">
                    </div>
                </div>
            </form>
        `;

        modalManager.show('Edit Basic Profile Info', content, async (formData) => {
            const saveResp = await fetch('/api/profile/basic-info', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': getCSRFToken()
                },
                body: JSON.stringify(formData)
            });

            const result = await saveResp.json();
            if (result.success) {
                showToast('Profile updated successfully!');
                location.reload();
                return true;
            }
            return false;
        }, 'large');

    } catch (e) {
        console.error('Error fetching basic info:', e);
        showToast('Failed to load profile data', 'error');
    }
}

// Make functions globally available
window.editHeadline = editHeadline;
window.addSkill = addSkill;
window.deleteSkill = deleteSkill;
window.addEmployment = addEmployment;
window.editEmployment = editEmployment;
window.deleteEmployment = deleteEmployment;
window.addEducation = addEducation;
window.editEducation = editEducation;
window.deleteEducation = deleteEducation;
window.addITSkill = addITSkill;
window.editITSkill = editITSkill;
window.deleteITSkill = deleteITSkill;
window.editSummary = editSummary;
window.editPersonalDetails = editPersonalDetails;
window.addLanguage = addLanguage;
window.editLanguage = editLanguage;
window.deleteLanguage = deleteLanguage;
window.openBasicInfoModal = openBasicInfoModal;
// Open the appropriate modal or section for the missing detail
function openMissingDetails(key) {
    // fallback to basic info
    if (!key) {
        openBasicInfoModal();
        return;
    }

    switch (key) {
        case 'basic_info':
        case 'personal_details':
            openBasicInfoModal();
            break;
        case 'summary':
            if (typeof editSummary === 'function') editSummary();
            break;
        case 'employment':
            if (typeof addEmployment === 'function') addEmployment();
            break;
        case 'skills':
            if (typeof addSkill === 'function') addSkill();
            break;
        case 'headline':
            if (typeof editHeadline === 'function') editHeadline();
            break;
        case 'resume':
            // scroll to resume upload section if present
            const el = document.getElementById('resume');
            if (el) {
                el.scrollIntoView({ behavior: 'smooth', block: 'center' });
            } else {
                // fallback to opening basic info
                openBasicInfoModal();
            }
            break;
        case 'career_profile':
            if (typeof editCareerProfile === 'function') {
                editCareerProfile();
            } else {
                openBasicInfoModal();
            }
            break;
        default:
            openBasicInfoModal();
    }
}
window.openMissingDetails = openMissingDetails;
