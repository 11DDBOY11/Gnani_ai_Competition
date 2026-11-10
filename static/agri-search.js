(() => {
  const $ = id => document.getElementById(id);
  const questionBox = $('questionBox');
  const recordButton = $('recordButton');
  const askButton = $('askButton');
  const answerCard = $('answerCard');
  const answerText = $('answerText');
  const statusText = $('statusText');
  const offlineNote = $('offlineNote');
  const micIcon = recordButton.innerHTML;
  const langQuery = new URLSearchParams(location.search).get('lang');
  let language = langQuery === 'en' || langQuery === 'kn' ? langQuery : readLanguage();
  let capture = null;
  let captureTimeout = null;
  let viewActive = true;
  let generation = 0;
  let transcriptController = null;
  let answerController = null;
  let speakController = null;
  let audio = null;
  let audioUrl = null;

  function renderSources(sources) {
    const card = $('sourcesCard');
    const list = $('sourcesList');
    if (!card || !list) return;
    list.innerHTML = '';
    if (!Array.isArray(sources) || sources.length === 0) {
      card.hidden = true;
      return;
    }
    sources.forEach(src => {
      const li = document.createElement('li');
      if (src.url) {
        const a = document.createElement('a');
        a.href = src.url;
        a.target = '_blank';
        a.rel = 'noopener noreferrer';
        a.textContent = src.title || src.source_id;
        li.appendChild(a);
      } else {
        li.textContent = src.title || src.source_id;
      }
      if (src.publisher) {
        const pub = document.createElement('span');
        pub.className = 'source-publisher';
        pub.textContent = ` — ${src.publisher}`;
        li.appendChild(pub);
      }
      list.appendChild(li);
    });
    card.hidden = false;
  }

  function readLanguage() {
    try { return localStorage.getItem('krishi-language') === 'en' ? 'en' : 'kn'; }
    catch (error) { return 'kn'; }
  }
  function text(kn, en) { return language === 'kn' ? kn : en; }
  function setStatus(kn, en) { statusText.textContent = text(kn, en); }
  function applyLanguage() {
    document.documentElement.lang = language;
    document.querySelectorAll('[data-kn][data-en]').forEach(node => {
      node.textContent = language === 'kn' ? node.dataset.kn : node.dataset.en;
    });
    document.querySelectorAll('.suggestion-button').forEach(button => {
      button.textContent = language === 'kn' ? button.dataset.questionKn : button.dataset.questionEn;
    });
    document.querySelectorAll('[data-language]').forEach(button => {
      button.setAttribute('aria-pressed', String(button.dataset.language === language));
    });
    questionBox.placeholder = language === 'kn' ? questionBox.dataset.placeholderKn : questionBox.dataset.placeholderEn;
    recordButton.setAttribute('aria-label', capture
      ? text('ರೆಕಾರ್ಡಿಂಗ್ ನಿಲ್ಲಿಸಿ', 'Stop recording')
      : text('ಮಾತನಾಡಲು ಮೈಕ್ ಒತ್ತಿ', 'Tap the microphone to speak'));
    $('homeLink').href = '/?lang=' + language;
    $('brandHomeLink').href = '/?lang=' + language;
    try { localStorage.setItem('krishi-language', language); } catch (error) {}
  }
  function stopLocalCapture() {
    const active = capture;
    if (!active) return;
    capture = null;
    clearTimeout(captureTimeout);
    captureTimeout = null;
    active.processor.onaudioprocess = null;
    try { active.source.disconnect(); active.processor.disconnect(); active.mute.disconnect(); } catch (error) {}
    try { active.stream.getTracks().forEach(track => track.stop()); } catch (error) {}
    try { active.context.close(); } catch (error) {}
    recordButton.setAttribute('aria-pressed', 'false');
    recordButton.innerHTML = micIcon;
    recordButton.setAttribute('aria-label', text('ಮಾತನಾಡಲು ಮೈಕ್ ಒತ್ತಿ', 'Tap the microphone to speak'));
  }
  function stopPlayback() {
    if (speakController) speakController.abort();
    speakController = null;
    if (audio) {
      audio.onended = null;
      audio.onerror = null;
      audio.pause();
      audio.removeAttribute('src');
      audio.load();
      audio = null;
    }
    if (audioUrl) URL.revokeObjectURL(audioUrl);
    audioUrl = null;
    $('stopButton').hidden = true;
    $('listenButton').disabled = false;
  }
  function cancelPending() {
    generation += 1;
    if (transcriptController) transcriptController.abort();
    if (answerController) answerController.abort();
    if (speakController) speakController.abort();
    transcriptController = answerController = speakController = null;
    stopLocalCapture();
    stopPlayback();
    recordButton.disabled = false;
    askButton.disabled = false;
    $('listenButton').disabled = false;
  }
  function updateConnection() {
    offlineNote.hidden = navigator.onLine;
  }

  async function startRecording() {
    if (!navigator.onLine) {
      setStatus('ಇಂಟರ್ನೆಟ್ ಸಂಪರ್ಕ ಬೇಕು. ಪ್ರಶ್ನೆಯನ್ನು ಬರೆಯಬಹುದು.', 'An internet connection is required. You can type your question.');
      return;
    }
    recordButton.disabled = true;
    setStatus('ಮೈಕ್ ಅನುಮತಿ ಕೇಳಲಾಗುತ್ತಿದೆ…', 'Requesting microphone access…');
    try {
      if (!navigator.mediaDevices?.getUserMedia) throw new Error('unsupported');
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: {channelCount: 1, echoCancellation: true, noiseSuppression: true}
      });
      if (!viewActive) {
        stream.getTracks().forEach(track => track.stop());
        return;
      }
      const AudioContextClass = window.AudioContext || window.webkitAudioContext;
      const context = new AudioContextClass();
      await context.resume();
      const source = context.createMediaStreamSource(stream);
      const processor = context.createScriptProcessor(4096, 1, 1);
      const mute = context.createGain();
      mute.gain.value = 0;
      const chunks = [];
      const ratio = context.sampleRate / 8000;
      processor.onaudioprocess = event => {
        if (!capture) return;
        const input = event.inputBuffer.getChannelData(0);
        const count = Math.floor(input.length / ratio);
        const pcm = new Int16Array(count);
        for (let i = 0; i < count; i++) {
          const pos = i * ratio;
          const left = Math.floor(pos);
          const fraction = pos - left;
          const right = input[Math.min(left + 1, input.length - 1)] || 0;
          const sample = input[left] * (1 - fraction) + right * fraction;
          pcm[i] = Math.max(-1, Math.min(1, sample)) * 32767;
        }
        if (pcm.length) chunks.push(pcm);
      };
      source.connect(processor);
      processor.connect(mute);
      mute.connect(context.destination);
      capture = {stream, context, source, processor, mute, chunks, language, startedAt: Date.now()};
      recordButton.disabled = false;
      recordButton.setAttribute('aria-pressed', 'true');
      recordButton.setAttribute('aria-label', text('ರೆಕಾರ್ಡಿಂಗ್ ನಿಲ್ಲಿಸಿ', 'Stop recording'));
      recordButton.innerHTML = '<svg viewBox="0 0 24 24" aria-hidden="true"><rect x="6" y="6" width="12" height="12" rx="2" fill="currentColor"/></svg>';
      setStatus('ಆಲಿಸುತ್ತಿದ್ದೇನೆ… ನಿಲ್ಲಿಸಲು ಮೈಕ್ ಒತ್ತಿ.', 'Listening… Tap the microphone to stop.');
      captureTimeout = setTimeout(() => {
        if (capture && Date.now() - capture.startedAt >= 60000) stopRecording();
      }, 60050);
    } catch (error) {
      recordButton.disabled = false;
      setStatus('ಮೈಕ್ ಬಳಸಲು ಆಗಲಿಲ್ಲ. ದಯವಿಟ್ಟು ಪ್ರಶ್ನೆಯನ್ನು ಬರೆಯಿರಿ.', 'Microphone unavailable. Please type your question.');
    }
  }
  function encodePcm(samples) {
    const bytes = new Uint8Array(samples.length * 2);
    const view = new DataView(bytes.buffer);
    samples.forEach((sample, index) => view.setInt16(index * 2, sample, true));
    return bytes;
  }
  async function stopRecording() {
    const active = capture;
    if (!active) return;
    stopLocalCapture();
    recordButton.disabled = true;
    if (transcriptController) transcriptController.abort();
    transcriptController = new AbortController();
    const controller = transcriptController;
    const currentGeneration = generation;
    setStatus('ಮಾತನ್ನು ಬರಹವಾಗಿಸುತ್ತಿದ್ದೇನೆ…', 'Converting speech…');
    try {
      const total = active.chunks.reduce((sum, chunk) => sum + chunk.length, 0);
      const samples = new Int16Array(total);
      let offset = 0;
      active.chunks.forEach(chunk => { samples.set(chunk, offset); offset += chunk.length; });
      if (!samples.length) throw new Error('empty');
      const response = await fetch('/api/agri-search/transcribe?language=' + active.language, {
        method: 'POST',
        headers: {'Content-Type': 'application/octet-stream'},
        body: encodePcm(samples),
        signal: controller.signal
      });
      const data = await response.json();
      if (!viewActive || currentGeneration !== generation || controller.signal.aborted) return;
      if (!response.ok) throw new Error('transcription');
      if (!data.transcript) throw new Error('empty');
      questionBox.value = data.transcript;
      questionBox.focus();
      setStatus('ಪ್ರಶ್ನೆಯನ್ನು ಪರಿಶೀಲಿಸಿ, ನಂತರ ಕೇಳಿ.', 'Review your question, then tap Ask.');
    } catch (error) {
      if (error.name !== 'AbortError' && viewActive && currentGeneration === generation) {
        setStatus('ಮಾತು ಗುರುತಿಸಲಾಗಲಿಲ್ಲ. ಮತ್ತೆ ಪ್ರಯತ್ನಿಸಿ ಅಥವಾ ಪ್ರಶ್ನೆಯನ್ನು ಬರೆಯಿರಿ.', 'Speech was not recognized. Try again or type your question.');
      }
    } finally {
      if (transcriptController === controller) transcriptController = null;
      if (viewActive && currentGeneration === generation) recordButton.disabled = false;
    }
  }
  recordButton.addEventListener('click', () => capture ? stopRecording() : startRecording());

  async function askQuestion() {
    const question = questionBox.value.trim();
    if (question.length < 5) {
      setStatus('ದಯವಿಟ್ಟು ನಿಮ್ಮ ಪ್ರಶ್ನೆಯನ್ನು ಬರೆಯಿರಿ ಅಥವಾ ಮಾತನಾಡಿ.', 'Please type or speak your question.');
      questionBox.focus();
      return;
    }
    if (!navigator.onLine) {
      updateConnection();
      setStatus('ಇಂಟರ್ನೆಟ್ ಸಂಪರ್ಕ ಬೇಕು. ಸಂಪರ್ಕವಾದಾಗ ಮತ್ತೆ ಪ್ರಯತ್ನಿಸಿ.', 'Connection required. Please try again when online.');
      return;
    }
    cancelPending();
    const currentGeneration = generation;
    answerController = new AbortController();
    const controller = answerController;
    askButton.disabled = true;
    recordButton.disabled = true;
    answerCard.hidden = true;
    renderSources([]);
    setStatus('ಮಾರ್ಗದರ್ಶನ ಸಿದ್ಧಪಡಿಸುತ್ತಿದ್ದೇನೆ…', 'Preparing guidance…');
    try {
      const response = await fetch('/api/agri-search', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({question, language}),
        signal: controller.signal
      });
      const data = await response.json();
      if (!viewActive || currentGeneration !== generation || controller.signal.aborted) return;
      if (!response.ok) throw new Error('answer');
      answerText.textContent = data.answer;
      renderSources(data.sources);
      answerCard.hidden = false;
      setStatus('ಉತ್ತರ ಸಿದ್ಧವಾಗಿದೆ.', 'Guidance is ready.');
    } catch (error) {
      if (error.name !== 'AbortError' && viewActive && currentGeneration === generation) {
        setStatus('ಏನೋ ತೊಂದರೆಯಾಗಿದೆ. ದಯವಿಟ್ಟು ಮತ್ತೆ ಪ್ರಯತ್ನಿಸಿ.', 'Something went wrong. Please try again.');
      }
    } finally {
      if (answerController === controller) answerController = null;
      if (viewActive && currentGeneration === generation) {
        askButton.disabled = false;
        recordButton.disabled = false;
      }
    }
  }
  askButton.addEventListener('click', askQuestion);
  questionBox.addEventListener('keydown', event => {
    if ((event.ctrlKey || event.metaKey) && event.key === 'Enter') askQuestion();
  });

  document.querySelectorAll('.suggestion-button').forEach(button => {
    button.addEventListener('click', () => {
      questionBox.value = language === 'kn' ? button.dataset.questionKn : button.dataset.questionEn;
      questionBox.focus();
      questionBox.setSelectionRange(questionBox.value.length, questionBox.value.length);
    });
  });
  document.querySelectorAll('[data-language]').forEach(button => {
    button.addEventListener('click', () => {
      const next = button.dataset.language;
      if (next === language) return;
      cancelPending();
      language = next;
      answerCard.hidden = true;
      renderSources([]);
      setStatus('','');
      applyLanguage();
    });
  });

  $('listenButton').addEventListener('click', async () => {
    if (!navigator.onLine) {
      setStatus('ಇಂಟರ್ನೆಟ್ ಸಂಪರ್ಕ ಬೇಕು. ಉತ್ತರವನ್ನು ಓದಬಹುದು.', 'An internet connection is required. You can read the answer.');
      return;
    }
    stopPlayback();
    speakController = new AbortController();
    const controller = speakController;
    const currentGeneration = generation;
    $('listenButton').disabled = true;
    setStatus('ಧ್ವನಿ ಸಿದ್ಧಪಡಿಸುತ್ತಿದ್ದೇನೆ…', 'Preparing audio…');
    try {
      const response = await fetch('/api/agri-search/speak', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({text: answerText.textContent, language}),
        signal: controller.signal
      });
      if (!viewActive || currentGeneration !== generation || controller.signal.aborted) return;
      if (!response.ok) throw new Error('speech');
      const blob = await response.blob();
      if (!viewActive || currentGeneration !== generation || controller.signal.aborted) return;
      audioUrl = URL.createObjectURL(blob);
      audio = new Audio(audioUrl);
      audio.onended = () => {
        stopPlayback();
        setStatus('ಉತ್ತರ ಮುಗಿದಿದೆ.', 'Playback finished.');
      };
      audio.onerror = () => {
        stopPlayback();
        setStatus('ಪಠ್ಯ ಉತ್ತರ ಇದೆ. ಧ್ವನಿ ಪ್ಲೇ ಆಗಲಿಲ್ಲ; ಮತ್ತೆ ಪ್ರಯತ್ನಿಸಿ.', 'The text answer is still available. Audio failed; please retry.');
      };
      $('stopButton').hidden = false;
      await audio.play();
      setStatus('ಕೇಳುತ್ತಿದ್ದೀರಿ…', 'Playing…');
    } catch (error) {
      if (error.name !== 'AbortError' && viewActive && currentGeneration === generation) {
        stopPlayback();
        setStatus('ಪಠ್ಯ ಉತ್ತರ ಇದೆ. ಧ್ವನಿ ಸಿದ್ಧವಾಗಲಿಲ್ಲ; ಮತ್ತೆ ಪ್ರಯತ್ನಿಸಿ.', 'The text answer is still available. Audio could not be prepared; please retry.');
      }
    } finally {
      if (speakController === controller) speakController = null;
      if (viewActive && currentGeneration === generation) $('listenButton').disabled = false;
    }
  });
  $('stopButton').addEventListener('click', () => {
    stopPlayback();
    setStatus('ಧ್ವನಿ ನಿಲ್ಲಿಸಲಾಗಿದೆ.', 'Playback stopped.');
  });

  document.querySelectorAll('a.home-link, a.brand').forEach(link => {
    link.addEventListener('click', () => { viewActive = false; cancelPending(); });
  });
  window.addEventListener('pagehide', () => { viewActive = false; cancelPending(); });
  window.addEventListener('online', updateConnection);
  window.addEventListener('offline', () => {
    updateConnection();
    setStatus('ಇಂಟರ್ನೆಟ್ ಸಂಪರ್ಕ ಕಡಿತವಾಗಿದೆ.', 'Internet connection lost.');
  });

  updateConnection();
  applyLanguage();
})();
