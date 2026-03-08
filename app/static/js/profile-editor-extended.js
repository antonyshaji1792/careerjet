/**
 * Profile Editor - Part 2: Projects, Accomplishments, Diversity, Career Profile
 */

// ============ PROJECTS ============
async function addProject() {
    const content = `
        <form>
            <div class="form-group">
                <label>Project Title *</label>
                <input type="text" name="title" class="form-control" required placeholder="e.g., E-commerce Platform">
            </div>
            <div class="form-row">
                <div class="form-group">
                    <label>Client</label>
                    <input type="text" name="client" class="form-control" placeholder="e.g., ABC Corp">
                </div>
                <div class="form-group">
                    <label>Status</label>
                    <select name="project_status" class="form-control">
                        <option value="In Progress">In Progress</option>
                        <option value="Finished">Finished</option>
                    </select>
                </div>
            </div>
            <div class="form-row">
                <div class="form-group">
                    <label>Start Date</label>
                    <input type="date" name="start_date" class="form-control">
                </div>
                <div class="form-group">
                    <label>End Date</label>
                    <input type="date" name="end_date" class="form-control">
                </div>
            </div>
            <div class="form-group">
                <label>Your Role</label>
                <input type="text" name="role" class="form-control" placeholder="e.g., Lead Developer">
            </div>
            <div class="form-group">
                <label>Team Size</label>
                <input type="number" name="team_size" class="form-control" placeholder="e.g., 5">
            </div>
            <div class="form-group">
                <label>Description</label>
                <textarea name="description" class="form-control" rows="4" placeholder="Describe the project and your contributions"></textarea>
            </div>
            <div class="form-group">
                <label>Skills Used</label>
                <input type="text" name="skills_used" class="form-control" placeholder="e.g., React, Node.js, MongoDB">
            </div>
            <div class="form-group">
                <label>Project URL</label>
                <input type="url" name="project_url" class="form-control" placeholder="https://example.com">
            </div>
        </form>
    `;

    modalManager.show('Add Project', content, async (formData) => {
        const response = await fetch('/api/profile/projects', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCSRFToken()
            },
            body: JSON.stringify(formData)
        });

        const result = await response.json();
        if (result.success) {
            showToast('Project added successfully!');
            location.reload();
            return true;
        }
        return false;
    }, 'large');
}

async function editProject(projId) {
    const response = await fetch('/api/profile/projects');
    const data = await response.json();
    const proj = data.data.find(p => p.id === projId);

    if (!proj) return;

    const content = `
        <form>
            <div class="form-group">
                <label>Project Title *</label>
                <input type="text" name="title" class="form-control" required value="${proj.title}">
            </div>
            <div class="form-row">
                <div class="form-group">
                    <label>Client</label>
                    <input type="text" name="client" class="form-control" value="${proj.client || ''}">
                </div>
                <div class="form-group">
                    <label>Status</label>
                    <select name="project_status" class="form-control">
                        <option value="In Progress" ${proj.project_status === 'In Progress' ? 'selected' : ''}>In Progress</option>
                        <option value="Finished" ${proj.project_status === 'Finished' ? 'selected' : ''}>Finished</option>
                    </select>
                </div>
            </div>
            <div class="form-row">
                <div class="form-group">
                    <label>Start Date</label>
                    <input type="date" name="start_date" class="form-control" value="${proj.start_date || ''}">
                </div>
                <div class="form-group">
                    <label>End Date</label>
                    <input type="date" name="end_date" class="form-control" value="${proj.end_date || ''}">
                </div>
            </div>
            <div class="form-group">
                <label>Your Role</label>
                <input type="text" name="role" class="form-control" value="${proj.role || ''}">
            </div>
            <div class="form-group">
                <label>Team Size</label>
                <input type="number" name="team_size" class="form-control" value="${proj.team_size || ''}">
            </div>
            <div class="form-group">
                <label>Description</label>
                <textarea name="description" class="form-control" rows="4">${proj.description || ''}</textarea>
            </div>
            <div class="form-group">
                <label>Skills Used</label>
                <input type="text" name="skills_used" class="form-control" value="${proj.skills_used || ''}">
            </div>
            <div class="form-group">
                <label>Project URL</label>
                <input type="url" name="project_url" class="form-control" value="${proj.project_url || ''}">
            </div>
        </form>
    `;

    modalManager.show('Edit Project', content, async (formData) => {
        const response = await fetch(`/api/profile/projects/${projId}`, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCSRFToken()
            },
            body: JSON.stringify(formData)
        });

        const result = await response.json();
        if (result.success) {
            showToast('Project updated successfully!');
            location.reload();
            return true;
        }
        return false;
    }, 'large');
}

async function deleteProject(projId) {
    modalManager.confirm('Are you sure you want to delete this project?', async () => {
        const response = await fetch(`/api/profile/projects/${projId}`, {
            method: 'DELETE',
            headers: {
                'X-CSRFToken': getCSRFToken()
            }
        });

        const result = await response.json();
        if (result.success) {
            showToast('Project deleted successfully!');
            location.reload();
        }
    });
}

// ============ ACCOMPLISHMENTS ============
async function addAccomplishment(type = 'online_profile') {
    const typeLabels = {
        'online_profile': 'Online Profile',
        'work_sample': 'Work Sample',
        'certification': 'Certification',
        'publication': 'Publication',
        'patent': 'Patent'
    };

    const content = `
        <form>
            <div class="form-group">
                <label>Type</label>
                <select name="type" class="form-control">
                    <option value="online_profile" ${type === 'online_profile' ? 'selected' : ''}>Online Profile</option>
                    <option value="work_sample" ${type === 'work_sample' ? 'selected' : ''}>Work Sample</option>
                    <option value="certification" ${type === 'certification' ? 'selected' : ''}>Certification</option>
                    <option value="publication" ${type === 'publication' ? 'selected' : ''}>Publication</option>
                    <option value="patent" ${type === 'patent' ? 'selected' : ''}>Patent</option>
                </select>
            </div>
            <div class="form-group">
                <label>Title *</label>
                <input type="text" name="title" class="form-control" required placeholder="e.g., LinkedIn Profile">
            </div>
            <div class="form-group">
                <label>URL</label>
                <input type="url" name="url" class="form-control" placeholder="https://example.com">
            </div>
            <div class="form-group">
                <label>Description</label>
                <textarea name="description" class="form-control" rows="3" placeholder="Brief description"></textarea>
            </div>
            <div class="form-row">
                <div class="form-group">
                    <label>Issued By</label>
                    <input type="text" name="issued_by" class="form-control" placeholder="e.g., Coursera">
                </div>
                <div class="form-group">
                    <label>Issue Date</label>
                    <input type="date" name="issued_date" class="form-control">
                </div>
            </div>
        </form>
    `;

    modalManager.show(`Add ${typeLabels[type]}`, content, async (formData) => {
        const response = await fetch('/api/profile/accomplishments', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCSRFToken()
            },
            body: JSON.stringify(formData)
        });

        const result = await response.json();
        if (result.success) {
            showToast('Accomplishment added successfully!');
            location.reload();
            return true;
        }
        return false;
    });
}

async function editAccomplishment(accId) {
    const response = await fetch('/api/profile/accomplishments');
    const data = await response.json();
    const acc = data.data.find(a => a.id === accId);

    if (!acc) return;

    const content = `
        <form>
            <div class="form-group">
                <label>Type</label>
                <select name="type" class="form-control">
                    <option value="online_profile" ${acc.type === 'online_profile' ? 'selected' : ''}>Online Profile</option>
                    <option value="work_sample" ${acc.type === 'work_sample' ? 'selected' : ''}>Work Sample</option>
                    <option value="certification" ${acc.type === 'certification' ? 'selected' : ''}>Certification</option>
                    <option value="publication" ${acc.type === 'publication' ? 'selected' : ''}>Publication</option>
                    <option value="patent" ${acc.type === 'patent' ? 'selected' : ''}>Patent</option>
                </select>
            </div>
            <div class="form-group">
                <label>Title *</label>
                <input type="text" name="title" class="form-control" required value="${acc.title}">
            </div>
            <div class="form-group">
                <label>URL</label>
                <input type="url" name="url" class="form-control" value="${acc.url || ''}">
            </div>
            <div class="form-group">
                <label>Description</label>
                <textarea name="description" class="form-control" rows="3">${acc.description || ''}</textarea>
            </div>
            <div class="form-row">
                <div class="form-group">
                    <label>Issued By</label>
                    <input type="text" name="issued_by" class="form-control" value="${acc.issued_by || ''}">
                </div>
                <div class="form-group">
                    <label>Issue Date</label>
                    <input type="date" name="issued_date" class="form-control" value="${acc.issued_date || ''}">
                </div>
            </div>
        </form>
    `;

    modalManager.show('Edit Accomplishment', content, async (formData) => {
        const response = await fetch(`/api/profile/accomplishments/${accId}`, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCSRFToken()
            },
            body: JSON.stringify(formData)
        });

        const result = await response.json();
        if (result.success) {
            showToast('Accomplishment updated successfully!');
            location.reload();
            return true;
        }
        return false;
    });
}

async function deleteAccomplishment(accId) {
    modalManager.confirm('Are you sure you want to delete this accomplishment?', async () => {
        const response = await fetch(`/api/profile/accomplishments/${accId}`, {
            method: 'DELETE',
            headers: {
                'X-CSRFToken': getCSRFToken()
            }
        });

        const result = await response.json();
        if (result.success) {
            showToast('Accomplishment deleted successfully!');
            location.reload();
        }
    });
}

// ============ DIVERSITY INFO ============
async function editDiversity() {
    const response = await fetch('/api/profile/diversity');
    const data = await response.json();
    const diversity = data.data || {};

    const content = `
        <form>
            <div class="form-group">
                <h4 style="font-size: 1rem; margin-bottom: 1rem;">Disability Information</h4>
                <label style="display: flex; align-items: center; gap: 1rem;">
                    <input type="checkbox" name="has_disability" ${diversity.has_disability ? 'checked' : ''} style="width: auto;">
                    <span>I have a disability</span>
                </label>
            </div>
            <div class="form-group">
                <label>Disability Type</label>
                <input type="text" name="disability_type" class="form-control" value="${diversity.disability_type || ''}" placeholder="e.g., Visual impairment">
            </div>
            
            <hr style="margin: 2rem 0; border: none; border-top: 1px solid #e5e7eb;">
            
            <div class="form-group">
                <h4 style="font-size: 1rem; margin-bottom: 1rem;">Military Experience</h4>
                <label style="display: flex; align-items: center; gap: 1rem;">
                    <input type="checkbox" name="has_military_experience" ${diversity.has_military_experience ? 'checked' : ''} style="width: auto;">
                    <span>I have military experience</span>
                </label>
            </div>
            <div class="form-group">
                <label>Military Branch</label>
                <input type="text" name="military_branch" class="form-control" value="${diversity.military_branch || ''}" placeholder="e.g., Army">
            </div>
            <div class="form-row">
                <div class="form-group">
                    <label>Start Date</label>
                    <input type="date" name="military_start_date" class="form-control" value="${diversity.military_start_date || ''}">
                </div>
                <div class="form-group">
                    <label>End Date</label>
                    <input type="date" name="military_end_date" class="form-control" value="${diversity.military_end_date || ''}">
                </div>
            </div>
            
            <hr style="margin: 2rem 0; border: none; border-top: 1px solid #e5e7eb;">
            
            <div class="form-group">
                <h4 style="font-size: 1rem; margin-bottom: 1rem;">Career Break</h4>
                <label style="display: flex; align-items: center; gap: 1rem;">
                    <input type="checkbox" name="has_career_break" ${diversity.has_career_break ? 'checked' : ''} style="width: auto;">
                    <span>I have taken a career break</span>
                </label>
            </div>
            <div class="form-group">
                <label>Reason for Career Break</label>
                <input type="text" name="career_break_reason" class="form-control" value="${diversity.career_break_reason || ''}" placeholder="e.g., Family care">
            </div>
            <div class="form-row">
                <div class="form-group">
                    <label>Start Date</label>
                    <input type="date" name="career_break_start_date" class="form-control" value="${diversity.career_break_start_date || ''}">
                </div>
                <div class="form-group">
                    <label>End Date</label>
                    <input type="date" name="career_break_end_date" class="form-control" value="${diversity.career_break_end_date || ''}">
                </div>
            </div>
        </form>
    `;

    modalManager.show('Edit Diversity & Inclusion', content, async (formData) => {
        const response = await fetch('/api/profile/diversity', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCSRFToken()
            },
            body: JSON.stringify(formData)
        });

        const result = await response.json();
        if (result.success) {
            showToast('Diversity information updated successfully!');
            location.reload();
            return true;
        }
        return false;
    }, 'large');
}

// ============ CAREER PROFILE ============
async function editCareerProfile() {
    const response = await fetch('/api/profile/career-profile');
    const data = await response.json();
    const career = data.data || {};

    const content = `
        <form>
            <div class="form-group">
                <label>Current Industry</label>
                <input type="text" name="current_industry" class="form-control" value="${career.current_industry || ''}" placeholder="e.g., Information Technology">
            </div>
            <div class="form-group">
                <label>Preferred Industries</label>
                <input type="text" name="preferred_industries" class="form-control" value="${career.preferred_industries || ''}" placeholder="e.g., IT, Finance, Healthcare (comma-separated)">
            </div>
            <div class="form-row">
                <div class="form-group">
                    <label>Current Salary (Annual)</label>
                    <input type="number" name="current_salary" class="form-control" value="${career.current_salary || ''}" placeholder="e.g., 1200000">
                </div>
                <div class="form-group">
                    <label>Expected Salary (Annual)</label>
                    <input type="number" name="expected_salary" class="form-control" value="${career.expected_salary || ''}" placeholder="e.g., 1500000">
                </div>
            </div>
            <div class="form-row">
                <div class="form-group">
                    <label>Preferred Shift</label>
                    <select name="preferred_shift" class="form-control">
                        <option value="">Select</option>
                        <option value="Day" ${career.preferred_shift === 'Day' ? 'selected' : ''}>Day</option>
                        <option value="Night" ${career.preferred_shift === 'Night' ? 'selected' : ''}>Night</option>
                        <option value="Flexible" ${career.preferred_shift === 'Flexible' ? 'selected' : ''}>Flexible</option>
                    </select>
                </div>
                <div class="form-group">
                    <label>Preferred Employment Type</label>
                    <select name="preferred_employment_type" class="form-control">
                        <option value="">Select</option>
                        <option value="Full-time" ${career.preferred_employment_type === 'Full-time' ? 'selected' : ''}>Full-time</option>
                        <option value="Part-time" ${career.preferred_employment_type === 'Part-time' ? 'selected' : ''}>Part-time</option>
                        <option value="Contract" ${career.preferred_employment_type === 'Contract' ? 'selected' : ''}>Contract</option>
                        <option value="Freelance" ${career.preferred_employment_type === 'Freelance' ? 'selected' : ''}>Freelance</option>
                    </select>
                </div>
            </div>
            <div class="form-group">
                <label style="display: flex; align-items: center; gap: 1rem;">
                    <input type="checkbox" name="willing_to_relocate" ${career.willing_to_relocate ? 'checked' : ''} style="width: auto;">
                    <span>Willing to relocate</span>
                </label>
            </div>
            <div class="form-group">
                <label>Preferred Work Locations</label>
                <input type="text" name="preferred_work_location" class="form-control" value="${career.preferred_work_location || ''}" placeholder="e.g., Bangalore, Mumbai, Remote (comma-separated)">
            </div>
            <div class="form-group">
                <label>Notice Period (days)</label>
                <input type="number" name="notice_period_days" class="form-control" value="${career.notice_period_days || ''}" placeholder="e.g., 30">
            </div>
        </form>
    `;

    modalManager.show('Edit Career Profile', content, async (formData) => {
        const response = await fetch('/api/profile/career-profile', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCSRFToken()
            },
            body: JSON.stringify(formData)
        });

        const result = await response.json();
        if (result.success) {
            showToast('Career profile updated successfully!');
            location.reload();
            return true;
        }
        return false;
    }, 'large');
}

// Make functions globally available
window.addProject = addProject;
window.editProject = editProject;
window.deleteProject = deleteProject;
window.addAccomplishment = addAccomplishment;
window.editAccomplishment = editAccomplishment;
window.deleteAccomplishment = deleteAccomplishment;
window.editDiversity = editDiversity;
window.editCareerProfile = editCareerProfile;
