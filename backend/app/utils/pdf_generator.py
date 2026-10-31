try:
    from weasyprint import HTML
except Exception:  # pragma: no cover - optional PDF generator support
    HTML = None
from jinja2 import Template

def generate_daily_report_pdf(report_data: dict) -> bytes:
    html_template = """
    <html>
    <head>
        <style>
            body { font-family: sans-serif; margin: 40px; }
            h1 { color: #2c3e50; }
            table { width: 100%; border-collapse: collapse; margin-top: 20px; }
            th, td { border: 1px solid #ccc; padding: 8px; text-align: left; }
            th { background-color: #f5f5f5; }
        </style>
    </head>
    <body>
        <h1>Daily Order - {{ date }} ({{ branch }})</h1>
        <p>Status: {{ status }}</p>
        <p>Summary: {{ summary }}</p>

        <h2>Customers</h2>
        <table>
            <tr><th>Name</th><th>Age</th><th>Gender</th></tr>
            {% for p in customers %}
            <tr><td>{{ p.name }}</td><td>{{ p.age }}</td><td>{{ p.gender }}</td></tr>
            {% endfor %}
        </table>

        <h2>Expenses</h2>
        <table>
            <tr><th>Category</th><th>Amount</th><th>Notes</th></tr>
            {% for e in expenses %}
            <tr><td>{{ e.category }}</td><td>{{ e.amount }}</td><td>{{ e.notes }}</td></tr>
            {% endfor %}
        </table>

        <h2>Notes</h2>
        <ul>
            {% for n in notes %}
            <li><strong>{{ n.author }}:</strong> {{ n.content }}</li>
            {% endfor %}
        </ul>

        <p><strong>Total Expense:</strong> ₹{{ total_expense }}</p>
    </body>
    </html>
    """

    template = Template(html_template)
    rendered_html = template.render(**report_data)
    if HTML is None:
        raise RuntimeError("PDF export is unavailable because the required native libraries are not installed")
    pdf = HTML(string=rendered_html).write_pdf()
    return pdf
def generate_invoice_pdf(invoice_data: dict) -> bytes:
    html_template = """
    <html>
    <head>
        <style>
            body { font-family: sans-serif; margin: 40px; }
            h1 { color: #2c3e50; }
            table { width: 100%; border-collapse: collapse; margin-top: 20px; }
            th, td { border: 1px solid #ccc; padding: 8px; text-align: left; }
            th { background-color: #f5f5f5; }
        </style>
    </head>
    <body>
        <h1>Invoice - VaidyaVihar Diagnostic</h1>
        <p><strong>Customer:</strong> {{ patient.name }} ({{ patient.gender }}, Age {{ patient.age }})</p>
        <p><strong>Date:</strong> {{ date }}</p>

        <h2>MenuItems</h2>
        <table>
            <tr><th>MenuItem Name</th><th>Result</th><th>Price</th></tr>
            {% for t in menu_items %}
            <tr><td>{{ t.test_name }}</td><td>{{ t.result }}</td><td>₹{{ t.price }}</td></tr>
            {% endfor %}
        </table>

        <h2>Billing</h2>
        <p><strong>Total:</strong> ₹{{ total }}</p>
        <p><strong>Paid:</strong> ₹{{ paid }}</p>
        <p><strong>Status:</strong> {{ status }}</p>
    </body>
    </html>
    """
    template = Template(html_template)
    rendered_html = template.render(**invoice_data)
    if HTML is None:
        raise RuntimeError("PDF export is unavailable because the required native libraries are not installed")
    pdf = HTML(string=rendered_html).write_pdf()
    return pdf