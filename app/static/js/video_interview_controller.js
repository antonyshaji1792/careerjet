/**
 * AI Video Interview Controller
 * Handles Media (Mic/Cam), Web Speech API (TTS/STT), and State Transitions.
 */

let sessionState = {
    status: 'IDLE', // IDLE, AVATAR_SPEAKING, USER_LISTENING, USER_RECORDING, PROCESSING
    currentQuestionIndex: 0,
    startTime: null,
    timerInterval: null,
    isMuted: false,
    cameraEnabled: false,
    localStream: null,
    recognition: null, // STT
    synth: window.speechSynthesis, // TTS
    lastTranscript: "",
    mediaRecorder: null,
    recordedChunks: []
};

let config = null;
let currentUtterance = null;

/**
 * Heuristic to find the most "human" sounding voice available in the browser.
 */
function getBestVoice(persona) {
    const voices = window.speechSynthesis.getVoices();
    if (voices.length === 0) return null;

    // Preference: Neural/Natural/Google/Microsoft/Premium voices
    const qualityKeywords = ['neural', 'natural', 'google', 'microsoft', 'enhanced', 'premium', 'natural'];
    const genderKeywords = (persona === 'sarah')
        ? ['susan', 'aria', 'samantha', 'zira', 'amy', 'sara', 'female']
        : ['david', 'guy', 'alex', 'mark', 'brian', 'male'];

    let candidates = voices.filter(v => v.lang.startsWith('en'));

    // Filter by gender if possible
    let genderMatches = candidates.filter(v =>
        genderKeywords.some(kw => v.name.toLowerCase().includes(kw))
    );

    if (genderMatches.length > 0) candidates = genderMatches;

    // Rank by quality type (e.g. "Natural" voices on Edge/Chrome are excellent)
    candidates.sort((a, b) => {
        const aScore = qualityKeywords.reduce((acc, kw) => acc + (a.name.toLowerCase().includes(kw) ? 1 : 0), 0);
        const bScore = qualityKeywords.reduce((acc, kw) => acc + (b.name.toLowerCase().includes(kw) ? 1 : 0), 0);
        return bScore - aScore;
    });

    const selected = candidates[0] || voices.find(v => v.lang.startsWith('en')) || voices[0];
    console.log(`Selected Voice: ${selected.name} (${selected.lang})`);
    return selected;
}

// Ensure voices are loaded
if (window.speechSynthesis.onvoiceschanged !== undefined) {
    window.speechSynthesis.onvoiceschanged = () => {
        console.log("Voices loaded/changed");
    };
}

async function initVideoInterview(setupConfig) {
    config = setupConfig;
    sessionState.currentQuestionIndex = 0;
    sessionState.cameraEnabled = config.cameraEnabled;
    sessionState.startTime = Date.now();

    updateStatusUI("Initializing session...");

    // 1. Setup Media
    try {
        sessionState.localStream = await navigator.mediaDevices.getUserMedia({
            audio: true,
            video: config.cameraEnabled
        });

        if (config.cameraEnabled) {
            document.getElementById('userFeed').srcObject = sessionState.localStream;
        }

        // Setup Video Recording
        setupRecording();
    } catch (err) {
        console.error("Hardware access error:", err);
        alert("Microphone access is required for the interview.");
        return;
    }

    // 2. Setup Speech Recognition
    setupSTT();

    // 3. Start Timer
    startTimer();

    // 4. Setup Control Listeners
    setupControlListeners();

    // 5. Start Interview Loop
    startInterviewLoop();
}

function setupControlListeners() {
    const micBtn = document.getElementById('micToggle');
    const camBtn = document.getElementById('camToggle');

    micBtn.addEventListener('click', () => {
        sessionState.isMuted = !sessionState.isMuted;
        const audioTrack = sessionState.localStream.getAudioTracks()[0];
        if (audioTrack) audioTrack.enabled = !sessionState.isMuted;

        micBtn.classList.toggle('btn-danger', sessionState.isMuted);
        micBtn.innerHTML = sessionState.isMuted ? '<i class="fas fa-microphone-slash"></i>' : '<i class="fas fa-microphone"></i>';
    });

    camBtn.addEventListener('click', () => {
        if (!config.cameraEnabled) return;
        sessionState.cameraEnabled = !sessionState.cameraEnabled;
        const videoTrack = sessionState.localStream.getVideoTracks()[0];
        if (videoTrack) videoTrack.enabled = sessionState.cameraEnabled;

        document.getElementById('userFeed').style.display = sessionState.cameraEnabled ? 'block' : 'none';
        camBtn.classList.toggle('btn-danger', !sessionState.cameraEnabled);
        camBtn.innerHTML = sessionState.cameraEnabled ? '<i class="fas fa-video"></i>' : '<i class="fas fa-video-slash"></i>';
    });
}

function stopInterviewMedia() {
    if (sessionState.localStream) {
        sessionState.localStream.getTracks().forEach(track => track.stop());
    }
    if (sessionState.recognition) {
        sessionState.recognition.stop();
    }
}

function setupRecording() {
    if (!sessionState.localStream) return;

    // Check supported types
    const mimeType = 'video/webm;codecs=vp8,opus';
    if (!MediaRecorder.isTypeSupported(mimeType)) {
        console.warn("Mime type not supported:", mimeType);
    }

    sessionState.mediaRecorder = new MediaRecorder(sessionState.localStream, {
        mimeType: mimeType
    });

    sessionState.mediaRecorder.ondataavailable = (event) => {
        if (event.data.size > 0) {
            sessionState.recordedChunks.push(event.data);
        }
    };

    sessionState.mediaRecorder.start(1000); // Collect data every 1s
    console.log("Recording started...");
}

async function stopAndUploadVideo() {
    return new Promise((resolve) => {
        if (!sessionState.mediaRecorder || sessionState.mediaRecorder.state === 'inactive') {
            resolve();
            return;
        }

        sessionState.mediaRecorder.onstop = async () => {
            const blob = new Blob(sessionState.recordedChunks, { type: 'video/webm' });
            const formData = new FormData();
            formData.append('video', blob, 'interview.webm');

            try {
                updateStatusUI("Uploading recording...");
                const response = await fetch(`/video-interview/upload-video/${config.sessionId}`, {
                    method: 'POST',
                    headers: {
                        'X-CSRFToken': config.csrfToken
                    },
                    body: formData
                });

                if (response.ok) {
                    console.log("Video uploaded successfully");
                } else {
                    console.error("Video upload failed");
                }
            } catch (err) {
                console.error("Upload error:", err);
            }
            resolve();
        };

        sessionState.mediaRecorder.stop();
    });
}

function setupSTT() {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SpeechRecognition) {
        console.warn("Speech Recognition not supported in this browser.");
        return;
    }

    sessionState.recognition = new SpeechRecognition();
    sessionState.recognition.continuous = true;
    sessionState.recognition.interimResults = true;
    sessionState.recognition.lang = 'en-US';

    sessionState.recognition.onresult = (event) => {
        let interimTranscript = '';
        for (let i = event.resultIndex; i < event.results.length; ++i) {
            if (event.results[i].isFinal) {
                sessionState.lastTranscript += event.results[i][0].transcript;
            } else {
                interimTranscript += event.results[i][0].transcript;
            }
        }

        if (sessionState.status === 'USER_LISTENING' || sessionState.status === 'USER_RECORDING') {
            onVoiceDetected();
        }
    };

    sessionState.recognition.onerror = (event) => {
        console.error("Speech Recognition Error:", event.error);
    };
}

async function startInterviewLoop() {
    const currentQuestion = config.questions[sessionState.currentQuestionIndex];
    if (!currentQuestion) {
        finishSession();
        return;
    }

    // Update Progress UI
    document.getElementById('qIndex').innerText = sessionState.currentQuestionIndex + 1;
    document.getElementById('qTotal').innerText = config.questions.length;

    // Transition to Speaking
    await speakQuestion(currentQuestion.question);
}

async function speakQuestion(text) {
    sessionState.status = 'AVATAR_SPEAKING';
    updateStatusUI(`${config.persona === 'sarah' ? 'Sarah' : 'Alex'} is speaking...`);
    showSubtitle(text);
    setAvatarMood('speaking');
    setStatusPulse('none');

    // Cancel any ongoing speech
    window.speechSynthesis.cancel();

    // Humanize speech by breaking into sentences and adding natural pauses
    const sentences = text.match(/[^.!?]+[.!?]*/g) || [text];

    for (let i = 0; i < sentences.length; i++) {
        if (sessionState.status !== 'AVATAR_SPEAKING') break; // Allow interruption if needed

        const sentence = sentences[i].trim();
        if (!sentence) continue;

        await new Promise((resolve) => {
            const utterance = new SpeechSynthesisUtterance(sentence);
            const voice = getBestVoice(config.persona);
            if (voice) utterance.voice = voice;

            // Add slight human variation (pitch/rate)
            utterance.pitch = (config.persona === 'sarah' ? 1.05 : 0.95) + (Math.random() * 0.04 - 0.02);
            utterance.rate = 0.95 + (Math.random() * 0.1 - 0.05);
            utterance.volume = 1.0;

            utterance.onend = resolve;
            utterance.onerror = (e) => {
                console.error("Speech Error:", e);
                resolve();
            };

            window.speechSynthesis.speak(utterance);
        });

        // Add a natural gap between sentences (mimics thinking/breathing)
        if (i < sentences.length - 1) {
            const delay = 400 + Math.random() * 400; // 400-800ms
            await new Promise(r => setTimeout(r, delay));
        }
    }

    setAvatarMood('neutral');
    startListening();
}

function startListening() {
    sessionState.status = 'USER_LISTENING';
    sessionState.lastTranscript = "";
    updateStatusUI("I'm listening...");
    setStatusPulse('listening');

    if (sessionState.recognition) {
        sessionState.recognition.start();
    }
}

let silenceTimer = null;

function onVoiceDetected() {
    if (sessionState.status === 'USER_LISTENING') {
        sessionState.status = 'USER_RECORDING';
        updateStatusUI("Recording answer...");
    }

    // Reset silence timer on every voice result
    if (silenceTimer) clearTimeout(silenceTimer);
    silenceTimer = setTimeout(() => {
        if (sessionState.status === 'USER_RECORDING') {
            submitAnswer();
        }
    }, 4000); // 4s silence threshold
}

async function submitAnswer() {
    if (sessionState.recognition) sessionState.recognition.stop();

    sessionState.status = 'PROCESSING';
    updateStatusUI("Thinking...");
    setStatusPulse('thinking');
    setAvatarMood('thinking');

    const payload = {
        session_id: config.sessionId,
        question_id: config.questions[sessionState.currentQuestionIndex].id,
        transcript: sessionState.lastTranscript,
        metadata: {
            duration_seconds: (Date.now() - sessionState.startTime) / 1000,
            word_count: sessionState.lastTranscript.split(' ').length
        }
    };

    try {
        const response = await fetch('/video-interview/api/v1/answer', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': config.csrfToken
            },
            body: JSON.stringify(payload)
        });

        const result = await response.json();

        // Reaction Speech (Nodding, feedback)
        if (result.reaction_text) {
            await speakQuestion(result.reaction_text);
        }

        // Move to next
        sessionState.currentQuestionIndex++;
        startInterviewLoop();

    } catch (err) {
        console.error("Submission error:", err);
        updateStatusUI("Error processing answer. Retrying...");
        setTimeout(submitAnswer, 2000);
    }
}

// UI Helpers
function updateStatusUI(text) {
    document.getElementById('statusLabel').innerText = text;
}

function showSubtitle(text) {
    const box = document.getElementById('subtitleText');
    box.innerText = text;
    box.classList.remove('d-none');
}

function setAvatarMood(mood) {
    const img = document.getElementById('avatarImage');
    const basePath = `/static/img/avatars/${config.persona}_`;
    const newSrc = `${basePath}${mood}.png`;

    // Create a temporary image to check if the mood exists
    const tempImg = new Image();
    tempImg.onload = () => img.src = newSrc;
    tempImg.onerror = () => {
        // Fallback to letters if mood-specific image is missing
        if (img.src.includes('ui-avatars')) return;
        img.src = `https://ui-avatars.com/api/?name=${config.persona}&background=6366f1&color=fff&size=512`;
    };
    tempImg.src = newSrc;
}

function setStatusPulse(type) {
    const pulse = document.getElementById('statusPulse');
    pulse.className = 'status-pulse';
    if (type !== 'none') pulse.classList.add(type);
}

function startTimer() {
    const timerEl = document.getElementById('sessionTimer');
    sessionState.timerInterval = setInterval(() => {
        const elapsed = Math.floor((Date.now() - sessionState.startTime) / 1000);
        const mm = String(Math.floor(elapsed / 60)).padStart(2, '0');
        const ss = String(elapsed % 60).padStart(2, '0');
        timerEl.innerText = `${mm}:${ss}`;
    }, 1000);
}

async function finishSession() {
    updateStatusUI("Finalizing session...");

    // Stop recording and upload
    await stopAndUploadVideo();

    if (sessionState.localStream) {
        sessionState.localStream.getTracks().forEach(t => t.stop());
    }
    if (sessionState.recognition) {
        sessionState.recognition.stop();
    }
    window.location.href = `/video-interview/results/${config.sessionId}`;
}
