document.addEventListener("DOMContentLoaded", function () {
  (function() {
    const tbody = document.getElementById('lo-tbody');
    if (!tbody) return;

    const sortable = new Sortable(tbody, {
      animation: 150,
      handle: '.drag-handle',
      ghostClass: 'table-active',
      onEnd: function() {
        const ids = Array.from(tbody.querySelectorAll('tr')).map(tr => tr.dataset.id);
        fetch(LO_REORDER_URL, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ order: ids, unit_id: UNIT_ID })
        }).then(r => r.json()).then(data => {
          if (!data.ok) {
            console.error('Reorder failed:', data.error);
            return;
          }
          Array.from(tbody.querySelectorAll('tr')).forEach((tr, idx) => {
            const firstCell = tr.querySelector('td');
            if (firstCell) firstCell.textContent = (idx + 1).toString();
          });
        }).catch(err => console.error(err));
      }
    });

    // Fixed evaluate button event listener
    document.getElementById('evaluateBtn')?.addEventListener('click', async function() {
      console.log('Evaluate button clicked'); // Debug log
      showLoading();

      try {
        // First save any changes before evaluating
        await autoSavePromise();

        const response = await fetch(AI_EVALUATE_URL, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'X-Requested-With': 'XMLHttpRequest'
          },
          body: JSON.stringify({ unit_id: UNIT_ID })
        });

        console.log('Response status:', response.status); // Debug log

        if (!response.ok) {
          throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }

        const data = await response.json();
        console.log('Response data:', data); // Debug log

        if (!data.ok) {
          throw new Error(data.error || 'Evaluation failed');
        }

        // Handle different response formats
        if (data.html) {
          // The server returns plain text in the 'html' field, not actual HTML
          console.log('Received data.html:', data.html); // Debug log
          formatAIResponse(data.html);
        } else if (data.evaluation) {
          // If the server returns evaluation text to be formatted
          formatAIResponse(data.evaluation);
        } else {
          // Fallback: try to format the entire response
          formatAIResponse(JSON.stringify(data));
        }

      } catch (error) {
        console.error('Evaluation error:', error); // Debug log
        showError(`Failed to evaluate outcomes: ${error.message}`);
      }
    });

  })();
});

// Convert autoSave to return a Promise for better error handling
function autoSavePromise() {
  return new Promise((resolve, reject) => {
    const loDict = {};
    const rows = document.getElementById("LOTable")?.rows;

    if (!rows || rows.length <= 1) {
      resolve(); // No data to save
      return;
    }

    for (let i = 1; i < rows.length; i++) {
      let pos = rows[i].cells[0]?.textContent?.trim();
      let desc = rows[i].cells[1]?.textContent?.trim() || '';
      let assessment = rows[i].cells[2]?.textContent?.trim() || '';
      if (pos) {
        loDict[pos] = [desc, assessment];
      }
    }

    fetch(LO_SAVE_URL, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(loDict)
    })
    .then(response => {
      if (response.ok) {
        resolve();
      } else {
        reject(new Error('Auto-save failed'));
      }
    })
    .catch(reject);
  });
}

function formatAIResponse(responseText) {
  const panel = document.getElementById('evaluationPanel');
  if (!panel) return;

  // Clear existing content
  panel.innerHTML = '';

  console.log('Raw AI response:', responseText); // Debug log

  try {
    // Check if responseText is actually text or if it needs to be extracted from an object
    if (typeof responseText === 'object') {
      responseText = JSON.stringify(responseText);
    }

    // Parse the AI response
    const { analysisSection, summarySection, outcomes } = parseAIResponse(responseText);

    // If no outcomes were parsed, try displaying the raw text with basic formatting
    if (outcomes.length === 0) {
      console.log('No outcomes parsed, using fallback display'); // Debug log
      displayFormattedText(responseText, panel);
      return;
    }

    // Create the formatted display
    const container = document.createElement('div');
    container.className = 'ai-evaluation-content';

/*    // Add LO Analysis header
    const analysisHeader = document.createElement('div');
    analysisHeader.className = 'alert alert-primary mb-3';
    analysisHeader.innerHTML = `
      <h6 class="alert-heading mb-2">
        <i class="bi bi-clipboard-data me-2"></i>
        <strong>LO Analysis</strong>
      </h6>
    `;
    container.appendChild(analysisHeader);*/

    // Add each outcome evaluation
    if (outcomes.length > 0) {
      outcomes.forEach((outcome, index) => {
        const card = createOutcomeCard(outcome, index + 1);
        container.appendChild(card);
      });
    }

    // Add Summary section if present
    if (summarySection) {
      const summaryDiv = document.createElement('div');
      summaryDiv.className = 'alert alert-info mt-4 mb-0';
      summaryDiv.innerHTML = `
        <h6 class="alert-heading mb-2">
          <i class="bi bi-list-check me-2"></i>
          <strong>SUMMARY</strong>
        </h6>
        <p class="mb-0 small">${formatTextWithLineBreaks(summarySection)}</p>
      `;
      container.appendChild(summaryDiv);
    }

    panel.appendChild(container);

  } catch (error) {
    console.error('Error in formatAIResponse:', error);
    console.error('Stack trace:', error.stack);
    // Fallback: display as formatted text
    displayFormattedText(responseText, panel);
  }
}

function parseAIResponse(responseText) {
  const outcomes = [];
  let summarySection = '';
  let analysisSection = '';

  console.log('Original response text:', responseText); // Debug log

  // Clean up the response text - handle both ** and regular markers
  responseText = responseText.replace(/\*\*LO Analysis:?\*\*/gi, 'LO_ANALYSIS_MARKER')
                             .replace(/\*\*SUMMARY:?\*\*/gi, 'SUMMARY_MARKER')
                             .replace(/^LO Analysis:?/gmi, 'LO_ANALYSIS_MARKER')
                             .replace(/^SUMMARY:?/gmi, 'SUMMARY_MARKER');

  // Split by SUMMARY to separate analysis from summary
  const summaryParts = responseText.split(/SUMMARY_MARKER/i);

  if (summaryParts.length > 1) {
    analysisSection = summaryParts[0];
    // Clean the summary section more thoroughly
    summarySection = summaryParts[1]
      .trim()
      .replace(/^[\s\n]+/, '') // Remove leading whitespace and newlines
      .replace(/[\s\n]+$/, '') // Remove trailing whitespace and newlines
      .replace(/_MARKER/gi, '') // Remove any leftover _MARKER text
      .replace(/^_+|_+$/g, ''); // Remove leading/trailing underscores
  } else {
    analysisSection = responseText;
  }

  // Remove LO Analysis header from analysis section
  analysisSection = analysisSection.replace(/LO_ANALYSIS_MARKER/gi, '').trim();

  console.log('Analysis section:', analysisSection); // Debug log
  console.log('Summary section:', summarySection); // Debug log

  // Parse outcomes with the new structured format
  // Look for pattern: 'outcome' - STATUS:[STATUS_VALUE] - feedback... SUGGESTION: 'suggestion'
  const lines = analysisSection.split('\n').filter(line => line.trim());

  let currentOutcome = null;
  let buildingFeedback = false;

  lines.forEach(line => {
    line = line.trim();
    if (!line) return;

    // Check if this line starts with a quote (beginning of an outcome)
    if (line.match(/^[''"]/)) {
      // Save previous outcome if exists
      if (currentOutcome && currentOutcome.text) {
        outcomes.push(currentOutcome);
      }

      // Parse the new outcome line
      // Pattern: 'outcome text' - STATUS:[STATUS] - feedback... SUGGESTION: 'suggestion'
      const fullPattern = /^[''""]([^''"]+)[''""][\s-]*STATUS:\s*(\w+)[\s-]*(.*)$/i;
      const match = line.match(fullPattern);

      if (match) {
        currentOutcome = {
          number: outcomes.length + 1,
          text: match[1].trim(),
          status: match[2].trim().toUpperCase(),
          feedback: match[3].trim().replace(/^-\s*/, '')
        };
        buildingFeedback = true;
      } else {
        // Fallback: try simpler pattern without STATUS tag
        const simplePattern = /^[''""]([^''"]+)[''""][\s-]*(.*)$/;
        const simpleMatch = line.match(simplePattern);

        if (simpleMatch) {
          currentOutcome = {
            number: outcomes.length + 1,
            text: simpleMatch[1].trim(),
            status: 'UNKNOWN',
            feedback: simpleMatch[2].trim().replace(/^-\s*/, '')
          };
          buildingFeedback = true;
        }
      }
    } else if (buildingFeedback && currentOutcome) {
      // This is a continuation of the current outcome's feedback
      currentOutcome.feedback += ' ' + line;
    }
  });

  // Don't forget the last outcome
  if (currentOutcome && currentOutcome.text) {
    outcomes.push(currentOutcome);
  }

  // Extract suggestions from feedback for each outcome
  outcomes.forEach(outcome => {
    const suggestionMatch = outcome.feedback.match(/SUGGESTION:\s*[''""]?([^''"]+)[''""]?/i);
    if (suggestionMatch) {
      outcome.suggestion = suggestionMatch[1].trim();
      // Remove the suggestion from the main feedback
      outcome.feedback = outcome.feedback.replace(/SUGGESTION:.*$/i, '').trim();
    }
  });

  console.log('Parsed outcomes:', outcomes); // Debug log

  return { analysisSection, summarySection, outcomes };
}

function createOutcomeCard(outcome, index) {
  const card = document.createElement('div');
  card.className = 'card mb-3 border-start border-4';

  // Determine styling based on STATUS tag first, then fallback to keyword detection
  let borderColor = 'border-secondary';
  let badgeClass = 'bg-secondary';
  let statusText = 'Unknown';
  let statusIcon = 'question-circle';

  // Use explicit STATUS if available
  if (outcome.status) {
    switch(outcome.status) {
      case 'GOOD':
        borderColor = 'border-success';
        badgeClass = 'bg-success';
        statusText = 'Good';
        statusIcon = 'check-circle-fill';
        break;
      case 'NEEDS_REVISION':
        borderColor = 'border-warning';
        badgeClass = 'bg-warning text-dark';
        statusText = 'Needs Revision';
        statusIcon = 'exclamation-triangle-fill';
        break;
      case 'COULD_IMPROVE':
        borderColor = 'border-info';
        badgeClass = 'bg-info';
        statusText = 'Could Improve';
        statusIcon = 'info-circle-fill';
        break;
      default:
        // If STATUS is not recognized, fall back to keyword detection
        const feedbackLower = outcome.feedback.toLowerCase();
        if (feedbackLower.includes('is good') ||
            feedbackLower.includes('is appropriate') ||
            feedbackLower.includes('appropriate for') ||
            feedbackLower.includes('correctly') ||
            feedbackLower.includes('well-aligned')) {
          borderColor = 'border-success';
          badgeClass = 'bg-success';
          statusText = 'Good';
          statusIcon = 'check-circle-fill';
        } else if (feedbackLower.includes('needs revision') ||
                   feedbackLower.includes('should be revised') ||
                   feedbackLower.includes('too high') ||
                   feedbackLower.includes('too low') ||
                   feedbackLower.includes('wrong level')) {
          borderColor = 'border-warning';
          badgeClass = 'bg-warning text-dark';
          statusText = 'Needs Revision';
          statusIcon = 'exclamation-triangle-fill';
        } else if (feedbackLower.includes('could improve') ||
                   feedbackLower.includes('could be strengthened') ||
                   feedbackLower.includes('consider')) {
          borderColor = 'border-info';
          badgeClass = 'bg-info';
          statusText = 'Could Improve';
          statusIcon = 'info-circle-fill';
        }
    }
  }

  card.className += ` ${borderColor}`;

  card.innerHTML = `
    <div class="card-body py-3 px-3">
      <div class="d-flex align-items-start">
        <span class="badge rounded-pill bg-primary me-2 mt-1">${index}</span>
        <div class="flex-grow-1">
          ${outcome.text ? `
            <p class="mb-2 small">
              <strong class="text-dark">Outcome:</strong> 
              <em class="text-secondary">"${outcome.text}"</em>
            </p>
          ` : ''}
          
          <div class="d-flex align-items-center mb-2">
            <span class="badge ${badgeClass} me-2">
              <i class="bi bi-${statusIcon} me-1"></i>
              ${statusText}
            </span>
          </div>
          
          <div class="mt-2">
            <p class="small text-muted mb-1">
              <i class="bi bi-chat-dots me-1"></i>
              <strong>Analysis:</strong>
            </p>
            <p class="small text-secondary mb-0">
              ${formatTextWithLineBreaks(outcome.feedback)}
            </p>
            
            ${outcome.suggestion ? `
              <div class="mt-2 p-2 bg-light rounded">
                <p class="small mb-0">
                  <i class="bi bi-lightbulb me-1 text-warning"></i>
                  <strong>Suggested revision:</strong>
                  <em class="text-success">"${outcome.suggestion}"</em>
                </p>
              </div>
            ` : ''}
          </div>
        </div>
      </div>
    </div>
  `;

  return card;
}

function formatTextWithLineBreaks(text) {
  // Preserve line breaks and format text
  return text
    .split('\n')
    .map(line => line.trim())
    .filter(line => line)
    .join('<br>')
    .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>'); // Convert **text** to bold
}

function displayFormattedText(text, panel) {
  // Enhanced fallback formatting for unparseable responses
  const container = document.createElement('div');
  container.className = 'p-2';

  // Clean the text
  text = text.trim();

  // Check if we have markers for LO Analysis and Summary
  const hasLOAnalysis = /\*?\*?LO Analysis\*?\*?/i.test(text);
  const hasSummary = /\*?\*?SUMMARY\*?\*?/i.test(text);

  if (hasLOAnalysis || hasSummary) {
    // Split by these markers
    const parts = text.split(/(\*?\*?(?:LO Analysis|SUMMARY)\*?\*?)/gi);

    parts.forEach((part, index) => {
      part = part.trim();
      if (!part) return;

      // Check if this is a header
      if (/\*?\*?LO Analysis\*?\*?/i.test(part)) {
        const headerDiv = document.createElement('div');
        headerDiv.className = 'alert alert-primary mb-3';
        headerDiv.innerHTML = `
          <h6 class="alert-heading mb-0">
            <i class="bi bi-clipboard-data me-2"></i>
            <strong>LO Analysis</strong>
          </h6>
        `;
        container.appendChild(headerDiv);
      } else if (/\*?\*?SUMMARY\*?\*?/i.test(part)) {
        const headerDiv = document.createElement('div');
        headerDiv.className = 'alert alert-info mb-3 mt-3';
        headerDiv.innerHTML = `
          <h6 class="alert-heading mb-0">
            <i class="bi bi-list-check me-2"></i>
            <strong>SUMMARY</strong>
          </h6>
        `;
        container.appendChild(headerDiv);
      } else {
        // This is content
        // Split by newlines and process each line
        const lines = part.split('\n').filter(line => line.trim());

        lines.forEach(line => {
          line = line.trim();
          if (!line) return;

          // Check if this looks like an outcome (starts with quote)
          if (line.match(/^[''"]/)) {
            const outcomeDiv = document.createElement('div');
            outcomeDiv.className = 'card mb-2 border-start border-primary border-3';
            outcomeDiv.innerHTML = `
              <div class="card-body py-2 px-3">
                <p class="small mb-0">${formatTextWithLineBreaks(line)}</p>
              </div>
            `;
            container.appendChild(outcomeDiv);
          } else {
            // Regular text
            const textDiv = document.createElement('div');
            textDiv.className = 'mb-2';
            textDiv.innerHTML = `<p class="small text-secondary mb-0">${formatTextWithLineBreaks(line)}</p>`;
            container.appendChild(textDiv);
          }
        });
      }
    });
  } else {
    // No clear structure, just format as paragraphs
    const lines = text.split('\n').filter(line => line.trim());

    lines.forEach(line => {
      const lineDiv = document.createElement('div');
      lineDiv.className = 'mb-2';

      // Check if line looks like it contains an outcome (has quotes)
      if (line.includes("'") || line.includes('"')) {
        lineDiv.innerHTML = `
          <div class="card border-start border-primary border-3">
            <div class="card-body py-2 px-3">
              <p class="small mb-0">${formatTextWithLineBreaks(line)}</p>
            </div>
          </div>
        `;
      } else {
        lineDiv.innerHTML = `<p class="small text-secondary mb-0">${formatTextWithLineBreaks(line)}</p>`;
      }

      container.appendChild(lineDiv);
    });
  }

  panel.appendChild(container);
}

// Function to show loading state
function showLoading() {
  const panel = document.getElementById('evaluationPanel');
  if (!panel) return;

  panel.innerHTML = `
    <div class="d-flex justify-content-center align-items-center py-5">
      <div class="text-center">
        <div class="spinner-border text-primary mb-3" role="status">
          <span class="visually-hidden">Loading...</span>
        </div>
        <p class="text-muted">Analyzing learning outcomes...</p>
      </div>
    </div>
  `;
}

// Function to show error state
function showError(message) {
  const panel = document.getElementById('evaluationPanel');
  if (!panel) return;

  panel.innerHTML = `
    <div class="alert alert-danger" role="alert">
      <i class="bi bi-exclamation-triangle-fill me-2"></i>
      <strong>Error:</strong> ${message}
    </div>
  `;
}