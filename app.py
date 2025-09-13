import os
from datetime import datetime, date
from typing import Optional

from flask import Flask, request, redirect, url_for, render_template_string, abort, flash
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)
app.config.update(
    SECRET_KEY="dev",  # demo only
    SQLALCHEMY_DATABASE_URI="sqlite:///health.db",
    SQLALCHEMY_TRACK_MODIFICATIONS=False,
)
db = SQLAlchemy(app)

# -----------------------------
# Models
# -----------------------------
class Patient(db.Model):
    __tablename__ = "patients"
    id = db.Column(db.Integer, primary_key=True)
    first_name = db.Column(db.String(120), nullable=False)
    last_name = db.Column(db.String(120), nullable=False)
    date_of_birth = db.Column(db.Date, nullable=True)
    sex = db.Column(db.String(20), nullable=True)
    phone = db.Column(db.String(40), nullable=True)

    visits = db.relationship("Visit", back_populates="patient", cascade="all, delete-orphan")
    medications = db.relationship("Medication", back_populates="patient", cascade="all, delete-orphan")
    allergies = db.relationship("Allergy", back_populates="patient", cascade="all, delete-orphan")

    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}".strip()


class Visit(db.Model):
    __tablename__ = "visits"
    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.Integer, db.ForeignKey("patients.id"), nullable=False)
    visit_date = db.Column(db.Date, nullable=True)
    reason = db.Column(db.String(255), nullable=True)
    notes = db.Column(db.Text, nullable=True)

    patient = db.relationship("Patient", back_populates="visits")


class Medication(db.Model):
    __tablename__ = "medications"
    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.Integer, db.ForeignKey("patients.id"), nullable=False)
    name = db.Column(db.String(255), nullable=False)
    dosage = db.Column(db.String(255), nullable=True)
    frequency = db.Column(db.String(255), nullable=True)

    patient = db.relationship("Patient", back_populates="medications")


class Allergy(db.Model):
    __tablename__ = "allergies"
    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.Integer, db.ForeignKey("patients.id"), nullable=False)
    allergen = db.Column(db.String(255), nullable=False)
    reaction = db.Column(db.String(255), nullable=True)
    severity = db.Column(db.String(255), nullable=True)

    patient = db.relationship("Patient", back_populates="allergies")


with app.app_context():
    db.create_all()


# -----------------------------
# Helpers
# -----------------------------
def parse_date(value: str) -> Optional[date]:
    if not value:
        return None
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError:
        return None


# -----------------------------
# Templates (inline for simplicity)
# -----------------------------
BASE_HTML = """
<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8">
    <title>EHR Demo</title>
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <link href="https://cdn.jsdelivr.net/npm/@picocss/pico@2.0.6/css/pico.min.css" rel="stylesheet">
    <style>
      main { max-width: 980px; margin: 2rem auto; }
      .actions { display: flex; gap: .5rem; flex-wrap: wrap; }
      table { width: 100%; }
      td, th { vertical-align: top; }
      .muted { color: #666; }
      form.inline { display: inline; }
      .grid-2 { display: grid; grid-template-columns: 1fr 1fr; gap: 1rem; }
    </style>
  </head>
  <body>
    <main>
      <nav>
        <ul>
          <li><strong>EHR Demo</strong></li>
        </ul>
        <ul>
          <li><a href="{{ url_for('index') }}">Patients</a></li>
          <li><a href="{{ url_for('new_patient') }}">New Patient</a></li>
        </ul>
      </nav>
      {% with messages = get_flashed_messages() %}
        {% if messages %}
          <article>
            {% for m in messages %}<p>{{ m }}</p>{% endfor %}
          </article>
        {% endif %}
      {% endwith %}
      {% block content %}{% endblock %}
      <footer class="muted" style="margin-top:2rem">Demo only. No auth. Do not use in production.</footer>
    </main>
  </body>
</html>
"""

INDEX_HTML = """
{% extends "base" %}
{% block content %}
  <h2>Patients</h2>
  {% if patients %}
    <table>
      <thead>
        <tr><th>Name</th><th>DOB</th><th>Sex</th><th>Phone</th><th></th></tr>
      </thead>
      <tbody>
        {% for p in patients %}
          <tr>
            <td><a href="{{ url_for('patient_detail', patient_id=p.id) }}">{{ p.full_name }}</a></td>
            <td>{{ p.date_of_birth or "" }}</td>
            <td>{{ p.sex or "" }}</td>
            <td>{{ p.phone or "" }}</td>
            <td class="actions">
              <a role="button" href="{{ url_for('edit_patient', patient_id=p.id) }}">Edit</a>
              <form class="inline" method="post" action="{{ url_for('delete_patient', patient_id=p.id) }}">
                <button class="secondary" onclick="return confirm('Delete this patient?')">Delete</button>
              </form>
            </td>
          </tr>
        {% endfor %}
      </tbody>
    </table>
  {% else %}
    <p class="muted">No patients yet.</p>
  {% endif %}
  <p><a role="button" href="{{ url_for('new_patient') }}">Add Patient</a></p>
{% endblock %}
"""

PATIENT_FORM_HTML = """
{% extends "base" %}
{% block content %}
  <h2>{{ 'Edit' if patient else 'New' }} Patient</h2>
  <form method="post">
    <div class="grid-2">
      <label>First name
        <input name="first_name" required value="{{ patient.first_name if patient else '' }}" />
      </label>
      <label>Last name
        <input name="last_name" required value="{{ patient.last_name if patient else '' }}" />
      </label>
      <label>Date of birth
        <input type="date" name="date_of_birth" value="{{ patient.date_of_birth if patient and patient.date_of_birth else '' }}" />
      </label>
      <label>Sex
        <input name="sex" value="{{ patient.sex if patient else '' }}" />
      </label>
      <label>Phone
        <input name="phone" value="{{ patient.phone if patient else '' }}" />
      </label>
    </div>
    <div class="actions" style="margin-top:1rem">
      <button type="submit">Save</button>
      <a role="button" class="secondary" href="{{ url_for('index') }}">Cancel</a>
    </div>
  </form>
{% endblock %}
"""

PATIENT_DETAIL_HTML = """
{% extends "base" %}
{% block content %}
  <h2>{{ patient.full_name }}</h2>
  <p class="muted">
    DOB: {{ patient.date_of_birth or '—' }} · Sex: {{ patient.sex or '—' }} · Phone: {{ patient.phone or '—' }}
  </p>
  <p class="actions">
    <a role="button" href="{{ url_for('edit_patient', patient_id=patient.id) }}">Edit Patient</a>
    <a role="button" class="secondary" href="{{ url_for('index') }}">Back</a>
  </p>

  <h3>Visits</h3>
  <details open>
    <summary>Add visit</summary>
    <form method="post" action="{{ url_for('add_visit', patient_id=patient.id) }}">
      <div class="grid-2">
        <label>Date
          <input type="date" name="visit_date" />
        </label>
        <label>Reason
          <input name="reason" />
        </label>
      </div>
      <label>Notes
        <textarea name="notes" rows="3"></textarea>
      </label>
      <button type="submit">Add Visit</button>
    </form>
  </details>
  {% if patient.visits %}
    <table>
      <thead><tr><th>Date</th><th>Reason</th><th>Notes</th><th></th></tr></thead>
      <tbody>
        {% for v in patient.visits|sort(attribute='visit_date', reverse=True) %}
          <tr>
            <td>{{ v.visit_date or '—' }}</td>
            <td>{{ v.reason or '—' }}</td>
            <td>{{ v.notes or '—' }}</td>
            <td>
              <form class="inline" method="post" action="{{ url_for('delete_visit', patient_id=patient.id, visit_id=v.id) }}">
                <button class="secondary">Delete</button>
              </form>
            </td>
          </tr>
        {% endfor %}
      </tbody>
    </table>
  {% else %}
    <p class="muted">No visits.</p>
  {% endif %}

  <h3>Medications</h3>
  <details open>
    <summary>Add medication</summary>
    <form method="post" action="{{ url_for('add_medication', patient_id=patient.id) }}">
      <div class="grid-2">
        <label>Name
          <input name="name" required />
        </label>
        <label>Dosage
          <input name="dosage" />
        </label>
        <label>Frequency
          <input name="frequency" />
        </label>
      </div>
      <button type="submit">Add Medication</button>
    </form>
  </details>
  {% if patient.medications %}
    <table>
      <thead><tr><th>Name</th><th>Dosage</th><th>Frequency</th><th></th></tr></thead>
      <tbody>
        {% for m in patient.medications %}
          <tr>
            <td>{{ m.name }}</td>
            <td>{{ m.dosage or '—' }}</td>
            <td>{{ m.frequency or '—' }}</td>
            <td>
              <form class="inline" method="post" action="{{ url_for('delete_medication', patient_id=patient.id, medication_id=m.id) }}">
                <button class="secondary">Delete</button>
              </form>
            </td>
          </tr>
        {% endfor %}
      </tbody>
    </table>
  {% else %}
    <p class="muted">No medications.</p>
  {% endif %}

  <h3>Allergies</h3>
  <details open>
    <summary>Add allergy</summary>
    <form method="post" action="{{ url_for('add_allergy', patient_id=patient.id) }}">
      <div class="grid-2">
        <label>Allergen
          <input name="allergen" required />
        </label>
        <label>Reaction
          <input name="reaction" />
        </label>
        <label>Severity
          <input name="severity" />
        </label>
      </div>
      <button type="submit">Add Allergy</button>
    </form>
  </details>
  {% if patient.allergies %}
    <table>
      <thead><tr><th>Allergen</th><th>Reaction</th><th>Severity</th><th></th></tr></thead>
      <tbody>
        {% for a in patient.allergies %}
          <tr>
            <td>{{ a.allergen }}</td>
            <td>{{ a.reaction or '—' }}</td>
            <td>{{ a.severity or '—' }}</td>
            <td>
              <form class="inline" method="post" action="{{ url_for('delete_allergy', patient_id=patient.id, allergy_id=a.id) }}">
                <button class="secondary">Delete</button>
              </form>
            </td>
          </tr>
        {% endfor %}
      </tbody>
    </table>
  {% else %}
    <p class="muted">No allergies.</p>
  {% endif %}
{% endblock %}
"""

# -----------------------------
# Routes
# -----------------------------
@app.route("/")
def index():
    patients = Patient.query.order_by(Patient.last_name, Patient.first_name).all()
    return render_template_string(INDEX_HTML, patients=patients, **{"base": BASE_HTML})


@app.route("/patients/new", methods=["GET", "POST"])
def new_patient():
    if request.method == "POST":
        first_name = request.form.get("first_name", "").strip()
        last_name = request.form.get("last_name", "").strip()
        if not first_name or not last_name:
            flash("First and last name are required")
            return redirect(url_for("new_patient"))
        patient = Patient(
            first_name=first_name,
            last_name=last_name,
            date_of_birth=parse_date(request.form.get("date_of_birth", "")),
            sex=request.form.get("sex") or None,
            phone=request.form.get("phone") or None,
        )
        db.session.add(patient)
        db.session.commit()
        return redirect(url_for("patient_detail", patient_id=patient.id))
    return render_template_string(PATIENT_FORM_HTML, patient=None, **{"base": BASE_HTML})


@app.route("/patients/<int:patient_id>/edit", methods=["GET", "POST"])
def edit_patient(patient_id: int):
    patient = Patient.query.get_or_404(patient_id)
    if request.method == "POST":
        patient.first_name = request.form.get("first_name", "").strip() or patient.first_name
        patient.last_name = request.form.get("last_name", "").strip() or patient.last_name
        patient.date_of_birth = parse_date(request.form.get("date_of_birth", "")) or patient.date_of_birth
        patient.sex = request.form.get("sex") or None
        patient.phone = request.form.get("phone") or None
        db.session.commit()
        return redirect(url_for("patient_detail", patient_id=patient.id))
    return render_template_string(PATIENT_FORM_HTML, patient=patient, **{"base": BASE_HTML})


@app.route("/patients/<int:patient_id>", methods=["GET"])
def patient_detail(patient_id: int):
    patient = Patient.query.get_or_404(patient_id)
    return render_template_string(PATIENT_DETAIL_HTML, patient=patient, **{"base": BASE_HTML})


@app.route("/patients/<int:patient_id>/delete", methods=["POST"])
def delete_patient(patient_id: int):
    patient = Patient.query.get_or_404(patient_id)
    db.session.delete(patient)
    db.session.commit()
    return redirect(url_for("index"))


# Visits
@app.route("/patients/<int:patient_id>/visits/new", methods=["POST"])
def add_visit(patient_id: int):
    patient = Patient.query.get_or_404(patient_id)
    visit = Visit(
        patient=patient,
        visit_date=parse_date(request.form.get("visit_date", "")),
        reason=request.form.get("reason") or None,
        notes=request.form.get("notes") or None,
    )
    db.session.add(visit)
    db.session.commit()
    return redirect(url_for("patient_detail", patient_id=patient.id))


@app.route("/patients/<int:patient_id>/visits/<int:visit_id>/delete", methods=["POST"])
def delete_visit(patient_id: int, visit_id: int):
    _ = Patient.query.get_or_404(patient_id)
    visit = Visit.query.get_or_404(visit_id)
    if visit.patient_id != patient_id:
        abort(404)
    db.session.delete(visit)
    db.session.commit()
    return redirect(url_for("patient_detail", patient_id=patient_id))


# Medications
@app.route("/patients/<int:patient_id>/medications/new", methods=["POST"])
def add_medication(patient_id: int):
    patient = Patient.query.get_or_404(patient_id)
    name = (request.form.get("name") or "").strip()
    if not name:
        flash("Medication name is required")
        return redirect(url_for("patient_detail", patient_id=patient.id))
    med = Medication(
        patient=patient,
        name=name,
        dosage=request.form.get("dosage") or None,
        frequency=request.form.get("frequency") or None,
    )
    db.session.add(med)
    db.session.commit()
    return redirect(url_for("patient_detail", patient_id=patient.id))


@app.route("/patients/<int:patient_id>/medications/<int:medication_id>/delete", methods=["POST"])
def delete_medication(patient_id: int, medication_id: int):
    _ = Patient.query.get_or_404(patient_id)
    med = Medication.query.get_or_404(medication_id)
    if med.patient_id != patient_id:
        abort(404)
    db.session.delete(med)
    db.session.commit()
    return redirect(url_for("patient_detail", patient_id=patient_id))


# Allergies
@app.route("/patients/<int:patient_id>/allergies/new", methods=["POST"])
def add_allergy(patient_id: int):
    patient = Patient.query.get_or_404(patient_id)
    allergen = (request.form.get("allergen") or "").strip()
    if not allergen:
        flash("Allergen is required")
        return redirect(url_for("patient_detail", patient_id=patient.id))
    allergy = Allergy(
        patient=patient,
        allergen=allergen,
        reaction=request.form.get("reaction") or None,
        severity=request.form.get("severity") or None,
    )
    db.session.add(allergy)
    db.session.commit()
    return redirect(url_for("patient_detail", patient_id=patient.id))


@app.route("/patients/<int:patient_id>/allergies/<int:allergy_id>/delete", methods=["POST"])
def delete_allergy(patient_id: int, allergy_id: int):
    _ = Patient.query.get_or_404(patient_id)
    allergy = Allergy.query.get_or_404(allergy_id)
    if allergy.patient_id != patient_id:
        abort(404)
    db.session.delete(allergy)
    db.session.commit()
    return redirect(url_for("patient_detail", patient_id=patient_id))


# Map simple names for inline inheritance
@app.context_processor
def inject_templates():
    return {"base": BASE_HTML}


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "5000"))
    app.run(host="0.0.0.0", port=port, debug=True)
