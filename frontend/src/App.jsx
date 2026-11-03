import React, { useEffect, useState } from "react";
import "./App.css";

const API_URL = "http://127.0.0.1:8000/api";

const initialStats = {
  total_predictions: 0,
  verified_predictions: 0,
  correct_predictions: 0,
  failed_predictions: 0,
  accuracy_percent: 0,
};

async function apiRequest(path, options = {}) {
  const response = await fetch(`${API_URL}${path}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...options.headers,
    },
  });

  const data = await response.json().catch(() => ({}));

  if (!response.ok) {
    throw new Error(
      typeof data.detail === "string"
        ? data.detail
        : `Request failed: ${response.status}`
    );
  }

  return data;
}

function App() {
  const [page, setPage] = useState("dashboard");
  const [stats, setStats] = useState(initialStats);
  const [predictions, setPredictions] = useState([]);
  const [failures, setFailures] = useState([]);
  const [lineage, setLineage] = useState([]);
  const [models, setModels] = useState([]);

  const [subject, setSubject] = useState("");
  const [emailText, setEmailText] = useState("");
  const [sender, setSender] = useState("");
  const [modelId, setModelId] = useState("");
  const [predictionResult, setPredictionResult] = useState(null);

  const [searchText, setSearchText] = useState("");
  const [similarResults, setSimilarResults] = useState([]);

  const [predictionId, setPredictionId] = useState("");
  const [actualClass, setActualClass] = useState("FINANCE");
  const [verifiedBy, setVerifiedBy] = useState("3");
  const [feedback, setFeedback] = useState("");

  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");

  const navigation = [
    ["dashboard", "Dashboard", "📊"],
    ["classify", "Email Classification", "📧"],
    ["search", "Vector Search", "🔍"],
    ["predictions", "Predictions", "🤖"],
    ["verify", "Verify Prediction", "✅"],
    ["failures", "Failure Investigation", "⚠️"],
    ["lineage", "Data Lineage", "🔗"],
  ];

  async function loadDashboard() {
    const data = await apiRequest("/dashboard");
    setStats(data);
  }

  async function loadPredictions() {
    const data = await apiRequest("/predictions");
    setPredictions(Array.isArray(data) ? data : []);
  }

  async function loadFailures() {
    const data = await apiRequest("/failures");
    setFailures(Array.isArray(data) ? data : []);
  }

  async function loadLineage() {
    const data = await apiRequest("/lineage");
    setLineage(Array.isArray(data) ? data : []);
  }

  async function loadModels() {
    const data = await apiRequest("/models");
    setModels(Array.isArray(data) ? data : []);
  }

  async function refreshData() {
    setError("");

    const results = await Promise.allSettled([
      loadDashboard(),
      loadPredictions(),
      loadFailures(),
      loadLineage(),
      loadModels(),
    ]);

    if (results.some((result) => result.status === "rejected")) {
      setError(
        "Some data could not be loaded. Check the FastAPI server and API endpoints."
      );
    }
  }

  useEffect(() => {
    refreshData();
  }, []);

  async function handleClassify(event) {
    event.preventDefault();
    setError("");
    setMessage("");

    if (!emailText.trim()) {
      setError("Please enter email content.");
      return;
    }

    if (!modelId) {
      setError("Please select a model.");
      return;
    }

    setLoading(true);

    try {
      const result = await apiRequest("/predict", {
        method: "POST",
        body: JSON.stringify({
          sender,
          subject,
          email_text: emailText,
          model_id: Number(modelId),
        }),
      });

      setPredictionResult(result);
      setMessage("Prediction generated and saved successfully.");
      await refreshData();
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  async function handleVectorSearch(event) {
    event.preventDefault();
    setError("");
    setSimilarResults([]);

    if (!searchText.trim()) {
      setError("Enter text to search.");
      return;
    }

    setLoading(true);

    try {
      const data = await apiRequest("/search", {
        method: "POST",
        body: JSON.stringify({
          query: searchText,
          limit: 5,
        }),
      });

      setSimilarResults(
        Array.isArray(data) ? data : data.results || []
      );
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  async function handleVerify(event) {
    event.preventDefault();
    setError("");
    setMessage("");

    if (!predictionId || !actualClass || !verifiedBy) {
      setError("Please complete all required fields.");
      return;
    }

    setLoading(true);

    try {
      await apiRequest("/verify", {
        method: "POST",
        body: JSON.stringify({
          prediction_id: Number(predictionId),
          actual_class: actualClass,
          user_id: Number(verifiedBy),
          comment: feedback,
        }),
      });

      setMessage("Prediction verified successfully.");
      setPredictionId("");
      setFeedback("");
      await refreshData();
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  function renderDashboard() {
    const cards = [
      ["Total Predictions", stats.total_predictions, "📧"],
      ["Verified Predictions", stats.verified_predictions, "🔍"],
      ["Correct Predictions", stats.correct_predictions, "✅"],
      ["Failed Predictions", stats.failed_predictions, "⚠️"],
      ["Model Accuracy", `${stats.accuracy_percent ?? 0}%`, "📊"],
    ];

    return (
      <div>
        <h2>System Dashboard</h2>
        <p>Overview of AI model performance and failures.</p>

        <div className="stats-grid">
          {cards.map(([label, value, icon]) => (
            <div className="stat-card" key={label}>
              <div className="stat-icon">{icon}</div>
              <h3>{value ?? 0}</h3>
              <p>{label}</p>
            </div>
          ))}
        </div>

        <div className="panel">
          <h3>System Overview</h3>
          <p>
            This system tracks model predictions, verified results,
            failures, investigator feedback, and data lineage.
          </p>
          <p>
            ChromaDB enables semantic retrieval of related historical
            failure cases.
          </p>
          <button onClick={refreshData}>Refresh Dashboard</button>
        </div>
      </div>
    );
  }

  function renderClassification() {
    return (
      <div>
        <h2>Email Classification</h2>
        <p>Classify an email using the trained machine-learning model.</p>

        <form className="panel" onSubmit={handleClassify}>
          <label>Model</label>
          <select
            value={modelId}
            onChange={(e) => setModelId(e.target.value)}
            required
          >
            <option value="">Select model</option>
            {models.map((model) => (
              <option key={model.model_id} value={model.model_id}>
                {model.model_name} ({model.model_version})
              </option>
            ))}
          </select>

          <label>Sender</label>
          <input
            value={sender}
            onChange={(e) => setSender(e.target.value)}
            placeholder="example@gmail.com"
          />

          <label>Subject</label>
          <input
            value={subject}
            onChange={(e) => setSubject(e.target.value)}
            placeholder="Enter email subject"
          />

          <label>Email Content</label>
          <textarea
            rows="7"
            value={emailText}
            onChange={(e) => setEmailText(e.target.value)}
            placeholder="Paste email content here..."
            required
          />

          <button disabled={loading} type="submit">
            {loading ? "Classifying..." : "Classify Email"}
          </button>
        </form>

        {predictionResult && (
          <div className="panel result-panel">
            <h3>Prediction Result</h3>
            <p>
              <strong>Prediction ID:</strong>{" "}
              {predictionResult.prediction_id}
            </p>
            <p>
              <strong>Predicted Class:</strong>{" "}
              {predictionResult.predicted_class}
            </p>
            <p>
              <strong>Confidence:</strong>{" "}
              {predictionResult.confidence_score != null
                ? `${(
                    Number(predictionResult.confidence_score) * 100
                  ).toFixed(1)}%`
                : "Not available"}
            </p>
          </div>
        )}
      </div>
    );
  }

  function renderSearch() {
    return (
      <div>
        <h2>Vector Similarity Search</h2>
        <p>
          Search historical email cases and model failures using
          ChromaDB.
        </p>

        <form className="panel" onSubmit={handleVectorSearch}>
          <label>Search Query</label>
          <textarea
            rows="5"
            value={searchText}
            onChange={(e) => setSearchText(e.target.value)}
            placeholder="Enter email content or describe a failure..."
            required
          />

          <button type="submit" disabled={loading}>
            {loading ? "Searching..." : "Search Similar Cases"}
          </button>
        </form>

        <h3>Similar Cases</h3>

        {similarResults.length === 0 ? (
          <p>No search results to display.</p>
        ) : (
          similarResults.map((item, index) => (
            <div
              className="panel result-panel"
              key={item.id || index}
            >
              <h3>Match {index + 1}</h3>

              <p>
                <strong>Content:</strong>{" "}
                {item.document || item.email_text || "N/A"}
              </p>

              <p>
                <strong>Prediction ID:</strong>{" "}
                {item.metadata?.prediction_id ?? "N/A"}
              </p>

              <p>
                <strong>Failure ID:</strong>{" "}
                {item.metadata?.failure_id ?? "N/A"}
              </p>

              {item.distance != null && (
                <p>
                  <strong>Vector Distance:</strong>{" "}
                  {Number(item.distance).toFixed(4)}
                </p>
              )}
            </div>
          ))
        )}
      </div>
    );
  }

  function renderPredictions() {
    return (
      <div>
        <h2>Prediction Records</h2>
        <p>Predictions stored in the MySQL database.</p>

        <div className="panel table-container">
          <table>
            <thead>
              <tr>
                <th>ID</th>
                <th>Model ID</th>
                <th>Email ID</th>
                <th>Predicted Class</th>
                <th>Confidence</th>
                <th>Actual Class</th>
                <th>Correct?</th>
              </tr>
            </thead>

            <tbody>
              {predictions.map((item) => (
                <tr key={item.prediction_id}>
                  <td>{item.prediction_id}</td>
                  <td>{item.model_id}</td>
                  <td>{item.email_id}</td>
                  <td>{item.predicted_class}</td>
                  <td>
                    {item.confidence_score == null
                      ? "N/A"
                      : `${(
                          Number(item.confidence_score) * 100
                        ).toFixed(1)}%`}
                  </td>
                  <td>{item.actual_class ?? "Pending"}</td>
                  <td>
                    {item.is_correct == null
                      ? "Pending"
                      : Number(item.is_correct) === 1
                      ? "Yes"
                      : "No"}
                  </td>
                </tr>
              ))}

              {predictions.length === 0 && (
                <tr>
                  <td colSpan="7">No predictions found.</td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    );
  }

  function renderVerification() {
    return (
      <div>
        <h2>Verify Model Prediction</h2>
        <p>
          Record the actual class and investigator feedback.
          MySQL triggers and stored procedures handle failure creation
          and lineage recording.
        </p>

        <form className="panel" onSubmit={handleVerify}>
          <label>Prediction ID</label>
          <input
            type="number"
            min="1"
            value={predictionId}
            onChange={(e) => setPredictionId(e.target.value)}
            placeholder="Enter prediction ID"
            required
          />

          <label>Actual Class</label>
          <select
            value={actualClass}
            onChange={(e) => setActualClass(e.target.value)}
          >
            <option value="FINANCE">FINANCE</option>
            <option value="WORK">WORK</option>
            <option value="SPAM">SPAM</option>
            <option value="PROMOTION">PROMOTION</option>
          </select>

          <label>Verifier User ID</label>
          <input
            type="number"
            min="1"
            value={verifiedBy}
            onChange={(e) => setVerifiedBy(e.target.value)}
            required
          />

          <label>Investigator Feedback</label>
          <textarea
            rows="5"
            value={feedback}
            onChange={(e) => setFeedback(e.target.value)}
            placeholder="Describe the prediction result..."
          />

          <button type="submit" disabled={loading}>
            {loading ? "Saving..." : "Verify Prediction"}
          </button>
        </form>
      </div>
    );
  }

  function renderFailures() {
    return (
      <div>
        <h2>Failure Investigation</h2>
        <p>Explore incorrectly classified emails and their causes.</p>

        <div className="panel table-container">
          <table>
            <thead>
              <tr>
                <th>Failure ID</th>
                <th>Prediction ID</th>
                <th>Subject</th>
                <th>Predicted</th>
                <th>Actual</th>
                <th>Failure Type</th>
                <th>Description</th>
              </tr>
            </thead>

            <tbody>
              {failures.map((item) => (
                <tr key={item.failure_id}>
                  <td>{item.failure_id}</td>
                  <td>{item.prediction_id}</td>
                  <td>{item.subject ?? "N/A"}</td>
                  <td>{item.predicted_class}</td>
                  <td>{item.actual_class}</td>
                  <td>{item.failure_type_name}</td>
                  <td>
                    {item.failure_description ||
                      item.description ||
                      "N/A"}
                  </td>
                </tr>
              ))}

              {failures.length === 0 && (
                <tr>
                  <td colSpan="7">No failures recorded.</td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    );
  }

  function renderLineage() {
    return (
      <div>
        <h2>Data Lineage</h2>
        <p>
          Trace predictions back to their input emails, datasets,
          model versions, verification records and feedback.
        </p>

        <div className="panel table-container">
          <table>
            <thead>
              <tr>
                <th>Lineage ID</th>
                <th>Prediction</th>
                <th>Email</th>
                <th>Dataset</th>
                <th>Model</th>
                <th>Version</th>
                <th>Actual Result</th>
                <th>Failure</th>
                <th>Feedback</th>
              </tr>
            </thead>

            <tbody>
              {lineage.map((item) => (
                <tr key={item.lineage_id}>
                  <td>{item.lineage_id}</td>
                  <td>{item.prediction_id}</td>
                  <td>{item.email_id}</td>
                  <td>{item.dataset_id}</td>
                  <td>{item.model_id}</td>
                  <td>{item.model_version}</td>
                  <td>{item.actual_id}</td>
                  <td>{item.failure_id ?? "None"}</td>
                  <td>{item.feedback_id ?? "None"}</td>
                </tr>
              ))}

              {lineage.length === 0 && (
                <tr>
                  <td colSpan="9">No lineage records found.</td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    );
  }

  function renderPage() {
    switch (page) {
      case "dashboard":
        return renderDashboard();
      case "classify":
        return renderClassification();
      case "search":
        return renderSearch();
      case "predictions":
        return renderPredictions();
      case "verify":
        return renderVerification();
      case "failures":
        return renderFailures();
      case "lineage":
        return renderLineage();
      default:
        return renderDashboard();
    }
  }

  return (
    <div className="app-container">
      <aside className="sidebar">
        <div className="sidebar-header">
          <h2>AI Failure System</h2>
          <p>Investigation & Data Lineage</p>
        </div>

        <nav>
          {navigation.map(([key, label, icon]) => (
            <button
              key={key}
              className={`nav-item ${
                page === key ? "active" : ""
              }`}
              onClick={() => {
                setPage(key);
                setError("");
                setMessage("");
              }}
            >
              <span>{icon}</span>
              <span>{label}</span>
            </button>
          ))}
        </nav>
      </aside>

      <main className="main-content">
        <header className="topbar">
          <div>
            <h1>AI Model Failure Investigation</h1>
            <p>Database Management and Analysis System</p>
          </div>
          <span className="status-label">MySQL + ChromaDB</span>
        </header>

        {error && (
          <div className="alert error-alert" role="alert">
            {error}
          </div>
        )}

        {message && (
          <div className="alert success-alert" role="status">
            {message}
          </div>
        )}

        <section className="page-content">
          {renderPage()}
        </section>
      </main>
    </div>
  );
}

export default App;
