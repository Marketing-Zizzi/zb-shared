"""zb_shared — geteilte Bibliotheken fuer Zitzelsberger-Apps.

Single-Source statt kopierter Module (Konsolidierung [d-303]). Einbindung pro App:
    pip install "zb-shared @ git+https://github.com/Marketing-Zizzi/zb-shared@v0.2.0"
    # mit PDF-Helfer (xhtml2pdf):
    pip install "zb-shared[pdf] @ git+https://github.com/Marketing-Zizzi/zb-shared@v0.2.0"

Module:
    ki_client  — kanonischer KI-Zugang (Vertex-Embeddings EU + Claude direct/Vertex-EU + Modell-Registry)
    mailer     — Resend-E-Mail-Versand (send_email / send_email_async / send_email_with_pdf)
    pdf        — duenne PDF-/HTML-Helfer (escape_html, format_date_de, logo_data_uri, html_to_pdf_bytes)
    (geplant)  — weitere Audit-Libs nach Bedarf (vision liegt bereits in ki_client.claude_model)
"""
__version__ = "0.2.2"
