import streamlit as st
import cv2
import numpy as np
import pandas as pd
import tempfile
import os
import io
import json
from datetime import datetime, date
from pathlib import Path

from ultralytics import YOLO
from violation_detector import detect_violations, draw_violations, is_valid_plate, generate_evidence_image, extract_plate_text
from utils import (
    init_db,
    save_violation,
    save_evidence,
    get_all_violations,
    get_violations_by_type,
    search_violations_by_plate,
    get_stats,
    format_timestamp,
    confidence_color,
    ensure_dirs,
    insert_violation,
)
from preprocessing import preprocess_image
from evaluation import ModelEvaluator
from report_generator import generate_pdf_report

st.set_page_config(page_title='Traffic Violation Detection', layout='wide')
st.title('Traffic Violation Detection System')

@st.cache_resource
def load_model(path='models/traffic_violation_best.pt'):
    return YOLO(path)

@st.cache_resource
def load_plate_model(path='models/license_plate_best.pt'):
    if Path(path).exists():
        return YOLO(path)
    return None

_model = None
_plate_model = None

def get_model():
    global _model
    if _model is None:
        _model = load_model()
    return _model

def get_plate_model():
    global _plate_model
    if _plate_model is None:
        _plate_model = load_plate_model()
    return _plate_model

_DEFAULTS = {
    'violations': [],
    'detections': [],
    'annotated_img': None,
    'raw_img': None,
    'processed': False,
    'saved_ids': [],
    'log_page': 1,
    'video_summary': None,
    'evidence_path': None,
}
for k, v in _DEFAULTS.items():
    if k not in st.session_state:
        st.session_state[k] = v

PAGES = ['Detection', 'Violations Log', 'Analytics', 'Evaluation', 'Reports']
saved_page = st.session_state.get('_page')
if saved_page not in PAGES:
    saved_page = PAGES[0]
page = st.sidebar.radio('Navigation', PAGES, index=PAGES.index(saved_page))
st.session_state['_page'] = page

st.sidebar.markdown('---')
st.sidebar.subheader('Config')
conf_threshold = st.sidebar.slider('Confidence threshold', 0.01, 0.9, 0.05, 0.01)
show_all_boxes = st.sidebar.checkbox('Show all detections', value=False)
enable_preprocessing = st.sidebar.checkbox('Enable preprocessing', value=False)
st.sidebar.markdown('---')
st.sidebar.caption('v1.0 - Traffic Violation Detection')

def show_violation_table(violations):
    if not violations:
        st.info('No violations to display.')
        return
    data = []
    for v in violations:
        conf = v['confidence']
        color = confidence_color(conf)
        data.append({
            'Type': v['type'],
            'Confidence': f"{conf:.2f}",
            'Conf badge': f'<span style="background:{color};color:#fff;padding:2px 8px;border-radius:10px;font-size:0.8em">{conf:.2f}</span>',
            'Plate': v.get('plate_text') or '-',
        })
    df = pd.DataFrame(data)
    st.write(df[['Type', 'Conf badge', 'Plate']].to_html(escape=False, index=False), unsafe_allow_html=True)

def filter_violations_by_threshold(violations, threshold):
    return [v for v in violations if v['confidence'] >= threshold]

_COLORS = [
    (255, 0, 0), (0, 255, 0), (0, 0, 255), (255, 255, 0),
    (255, 0, 255), (0, 255, 255), (128, 0, 0), (0, 128, 0),
    (0, 0, 128), (128, 128, 0), (128, 0, 128), (0, 128, 128),
]

def draw_all_boxes(image, results):
    img = image.copy()
    boxes = results[0].boxes
    names = results[0].names
    if boxes is None:
        return img
    for i in range(len(boxes)):
        x1, y1, x2, y2 = map(int, boxes.xyxy[i].tolist())
        cls_id = int(boxes.cls[i].item())
        conf   = boxes.conf[i].item()
        color  = _COLORS[cls_id % len(_COLORS)]
        label  = f"{names[cls_id]} {conf:.2f}"
        cv2.rectangle(img, (x1, y1), (x2, y2), color, 2)
        cv2.putText(img, label, (x1, max(y1 - 5, 15)), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)
    return img

if page == PAGES[0]:
    st.header('Detection')

    uploaded = st.file_uploader('Upload an image or video', type=['jpg', 'jpeg', 'png', 'mp4'])

    if uploaded is not None:
        name = uploaded.name.lower()
        is_video = name.endswith('.mp4')
        suffix = '.mp4' if is_video else os.path.splitext(name)[1] or '.jpg'
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            tmp.write(uploaded.read())
            tmp_path = tmp.name

        if not is_video:
            raw = cv2.imread(tmp_path)
            if raw is not None:
                st.session_state.raw_img = cv2.cvtColor(raw, cv2.COLOR_BGR2RGB)
                st.session_state.uploaded_bytes = uploaded
                st.image(st.session_state.raw_img, caption='Original', channels='RGB')

                if enable_preprocessing:
                    with st.spinner('Applying preprocessing...'):
                        enhanced = preprocess_image(raw)
                        enhanced_rgb = cv2.cvtColor(enhanced, cv2.COLOR_BGR2RGB)
                        st.image(enhanced_rgb, caption='Enhanced', channels='RGB')
                        cv2.imwrite(tmp_path, enhanced)

        if not is_video:
            col1, col2 = st.columns([1, 1])

            with col1:
                detect_btn = st.button('Detect Violations', type='primary')

            if detect_btn or st.session_state.processed:
                if detect_btn:
                    with st.spinner('Running detection...'):
                        try:
                            all_violations, all_detections = detect_violations(tmp_path, enable_preprocessing=enable_preprocessing)
                            filtered = filter_violations_by_threshold(all_violations, conf_threshold)
                            st.session_state.violations = filtered
                            st.session_state.detections = all_detections

                            if show_all_boxes:
                                model = get_model()
                                res = model(tmp_path)
                                base = draw_all_boxes(cv2.imread(tmp_path), res)
                                annotated = draw_violations(base, filtered)
                            else:
                                annotated = draw_violations(tmp_path, filtered)

                            st.session_state.annotated_img = cv2.cvtColor(annotated, cv2.COLOR_BGR2RGB)
                            st.session_state.processed = True
                        except Exception as exc:
                            st.error(f'Detection failed: {exc}')

                if st.session_state.annotated_img is not None:
                    with col2:
                        st.image(st.session_state.annotated_img, caption='Annotated', channels='RGB')

                    detections = st.session_state.detections
                    violations = st.session_state.violations

                    if detections:
                        st.subheader('Detected Objects')
                        det_df = pd.DataFrame([
                            {'Class': d['class_name'], 'Confidence': f"{d['confidence']:.3f}"}
                            for d in detections
                        ])
                        st.dataframe(det_df, use_container_width=True, hide_index=True)

                        riders = [d for d in detections if d['class_name'] == 'person_rider']
                        vehicles = [d for d in detections if d['class_name'] == 'vehicle']
                        helmets = [d for d in detections if d['class_name'] == 'helmet']
                        seatbelts = [d for d in detections if d['class_name'] == 'seatbelt']
                        col_s1, col_s2, col_s3, col_s4 = st.columns(4)
                        with col_s1:
                            st.metric('Vehicles', len(vehicles))
                        with col_s2:
                            st.metric('Riders', len(riders))
                        with col_s3:
                            st.metric('Helmets', len(helmets))
                        with col_s4:
                            st.metric('Seatbelts', len(seatbelts))

                    if violations:
                        st.subheader(f'{len(violations)} violation(s) detected')
                        show_violation_table(violations)

                        col_save, col_report = st.columns(2)
                        with col_save:
                            if st.button('Save to Database', type='secondary'):
                                saved = 0
                                ensure_dirs()
                                for v in violations:
                                    img_bgr = cv2.cvtColor(st.session_state.annotated_img, cv2.COLOR_RGB2BGR)
                                    ev_path = save_evidence(img_bgr, v['type'])
                                    row_id = save_violation(
                                        v_type=v['type'],
                                        plate=v.get('plate_text'),
                                        confidence=v['confidence'],
                                        image_path=ev_path,
                                    )
                                    saved += 1
                                    st.session_state.saved_ids.append(row_id)
                                st.success(f'Saved {saved} violation(s) to database.')
                        with col_report:
                            if st.button('Generate PDF Report', type='secondary'):
                                ensure_dirs()
                                stats = get_stats()
                                pdf_path = generate_pdf_report(violations, stats)
                                with open(pdf_path, 'rb') as f:
                                    st.download_button(
                                        label='Download Report',
                                        data=f,
                                        file_name=os.path.basename(pdf_path),
                                        mime='application/pdf',
                                    )
                    else:
                        st.info('No violations detected. Try lowering the confidence threshold in the sidebar.')

        else:
            st.info('Video uploaded - processing every 30th frame.')
            process_vid = st.button('Process Video', type='primary')

            if process_vid:
                cap = cv2.VideoCapture(tmp_path)
                total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
                fps_rate = cap.get(cv2.CAP_PROP_FPS)
                duration = total_frames / fps_rate if fps_rate > 0 else 0
                st.write(f'Frames: {total_frames}  |  FPS: {fps_rate:.1f}  |  Duration: {duration:.1f}s')
                all_violations = {}
                frame_count = 0
                processed = 0
                prog = st.progress(0)
                while True:
                    ret, frame = cap.read()
                    if not ret:
                        break
                    if frame_count % 30 == 0:
                        processed += 1
                        prog.progress(min(processed * 30 / total_frames, 1.0))
                        with tempfile.NamedTemporaryFile(delete=False, suffix='.jpg') as f:
                            tmp_frame = f.name
                        cv2.imwrite(tmp_frame, frame)
                        try:
                            frame_violations, _ = detect_violations(tmp_frame)
                            filtered = filter_violations_by_threshold(frame_violations, conf_threshold)
                            for v in filtered:
                                key = (v['type'], v.get('plate_text'))
                                if key not in all_violations:
                                    all_violations[key] = {'type': v['type'], 'plate': v.get('plate_text'), 'count': 0, 'avg_conf': 0.0}
                                all_violations[key]['count'] += 1
                                all_violations[key]['avg_conf'] += v['confidence']
                        except Exception:
                            pass
                        finally:
                            if os.path.exists(tmp_frame):
                                os.unlink(tmp_frame)
                    frame_count += 1
                cap.release()
                prog.empty()
                for k, v in all_violations.items():
                    v['avg_conf'] /= v['count']
                summary = sorted(all_violations.values(), key=lambda x: x['count'], reverse=True)
                st.session_state.video_summary = summary
                if summary:
                    st.subheader('Video Summary')
                    rows = []
                    for s in summary:
                        rows.append({'Type': s['type'], 'Plate': s['plate'] or '-', 'Frames with violation': s['count'], 'Avg confidence': f"{s['avg_conf']:.2f}"})
                    st.dataframe(pd.DataFrame(rows), use_container_width=True)
                else:
                    st.info('No violations detected in the video.')
            if st.session_state.video_summary:
                if st.button('Save Video Summary to Database'):
                    saved = 0
                    ensure_dirs()
                    for s in st.session_state.video_summary:
                        save_violation(v_type=s['type'], plate=s['plate'], confidence=round(s['avg_conf'], 2), image_path=None)
                        saved += 1
                    st.success(f'Saved {saved} violation summary record(s) to database.')

        try:
            os.unlink(tmp_path)
        except Exception:
            pass

    else:
        st.info('Upload an image (jpg/png) or video (mp4) to begin.')
        st.session_state.processed = False
        st.session_state.violations = []

elif page == PAGES[1]:
    st.header('Violations Log')

    init_db()
    all_rows = get_all_violations()

    if not all_rows:
        st.info('No violations recorded yet. Run detection and save results first.')
    else:
        df = pd.DataFrame(all_rows)

        col1, col2, col3, col4 = st.columns(4)
        with col1:
            types = ['All'] + sorted(df['violation_type'].unique().tolist())
            sel_type = st.selectbox('Filter by type', types)
        with col2:
            dates = pd.to_datetime(df['timestamp']).dt.date
            min_date = dates.min()
            max_date = dates.max()
            date_range = st.date_input('Date range', value=(min_date, max_date), min_value=min_date, max_value=max_date)
        with col3:
            plate_search = st.text_input('Search by plate', '')
        with col4:
            st.markdown(f'**Total records:** {len(df)}')

        filtered = df.copy()
        if sel_type != 'All':
            filtered = filtered[filtered['violation_type'] == sel_type]
        if isinstance(date_range, tuple) and len(date_range) == 2:
            d_start, d_end = date_range
            filtered = filtered[
                (pd.to_datetime(filtered['timestamp']).dt.date >= d_start) &
                (pd.to_datetime(filtered['timestamp']).dt.date <= d_end)
            ]
        if plate_search:
            filtered = filtered[filtered['plate_number'].str.contains(plate_search, na=False, case=False)]

        per_page = 10
        total_pages = max(1, (len(filtered) + per_page - 1) // per_page)
        page_num = st.session_state.log_page
        if page_num > total_pages:
            page_num = total_pages
            st.session_state.log_page = page_num

        start_idx = (page_num - 1) * per_page
        end_idx = start_idx + per_page
        page_df = filtered.iloc[start_idx:end_idx]

        display = page_df[[
            'id', 'timestamp', 'violation_type', 'license_plate',
            'confidence', 'image_path', 'evidence_id',
        ]].copy()
        display.columns = ['ID', 'Timestamp', 'Type', 'Plate', 'Confidence', 'Evidence', 'Evidence ID']
        display['Confidence'] = display['Confidence'].apply(lambda x: f"{x:.2f}")
        st.dataframe(display, use_container_width=True, hide_index=True)

        col_p1, col_p2, col_p3 = st.columns([2, 6, 2])
        with col_p1:
            if st.button('Prev') and page_num > 1:
                st.session_state.log_page -= 1
                st.rerun()
        with col_p2:
            st.markdown(f"<div style='text-align:center'>Page {page_num} of {total_pages} ({len(filtered)} records)</div>", unsafe_allow_html=True)
        with col_p3:
            if st.button('Next') and page_num < total_pages:
                st.session_state.log_page += 1
                st.rerun()

        csv_buf = io.BytesIO()
        filtered.to_csv(csv_buf, index=False)
        csv_buf.seek(0)
        st.download_button(
            label='Download CSV',
            data=csv_buf,
            file_name=f'violations_{date.today().isoformat()}.csv',
            mime='text/csv',
        )

elif page == PAGES[2]:
    st.header('Analytics')

    init_db()
    stats = get_stats()
    rows = get_all_violations()

    if not rows:
        st.info('No data yet. Run detection and save violations to see analytics.')
    else:
        k1, k2, k3, k4 = st.columns(4)
        with k1:
            st.metric('Total Violations', stats['total'])
        with k2:
            type_count = len(stats['by_type'])
            st.metric('Violation Types', type_count)
        with k3:
            plate_count = len({r['license_plate'] for r in rows if r.get('license_plate')})
            st.metric('Unique Plates', plate_count)
        with k4:
            st.metric('Total Vehicles', stats.get('total_vehicles', 0))

        st.markdown('---')

        st.subheader('Violations by Type')
        by_type = stats['by_type']
        if by_type:
            bar_df = pd.DataFrame({'Type': list(by_type.keys()), 'Count': list(by_type.values())}).set_index('Type')
            st.bar_chart(bar_df, height=350)

        st.subheader('Daily Violation Count')
        by_date = stats['by_date']
        if by_date:
            line_df = pd.DataFrame({'Date': list(by_date.keys()), 'Count': list(by_date.values())})
            line_df['Date'] = pd.to_datetime(line_df['Date'])
            line_df = line_df.sort_values('Date').set_index('Date')
            st.line_chart(line_df, height=350)

        st.subheader('Top License Plates')
        plates = [r['license_plate'] for r in rows if r.get('license_plate')]
        if plates:
            plate_series = pd.Series(plates).value_counts().head(10)
            pie_df = pd.DataFrame({'Plate': plate_series.index, 'Count': plate_series.values})
            try:
                import plotly.express as px
                fig = px.pie(pie_df, names='Plate', values='Count', title='Top 10 Plates by Violation Count', color_discrete_sequence=px.colors.qualifier.Set3)
                st.plotly_chart(fig, use_container_width=True)
            except ImportError:
                try:
                    import matplotlib.pyplot as plt
                    fig2, ax = plt.subplots(figsize=(6, 6))
                    labels = [f"{r} ({c})" for r, c in zip(pie_df['Plate'], pie_df['Count'])]
                    ax.pie(pie_df['Count'], labels=labels, startangle=90, counterclock=False)
                    ax.set_title('Top 10 Plates')
                    st.pyplot(fig2)
                except ImportError:
                    st.dataframe(pie_df, use_container_width=True, hide_index=True)
        else:
            st.info('No license plate data recorded yet.')

        st.markdown('---')
        st.subheader('Compliance Metrics')
        total_violations = stats['total']
        no_helmet_count = stats['by_type'].get('NO HELMET', 0)
        no_seatbelt_count = stats['by_type'].get('NO SEATBELT', 0)
        triple_riding_count = stats['by_type'].get('TRIPLE RIDING', 0)

        if total_violations > 0:
            helmet_compliance = max(0, (1 - no_helmet_count / total_violations)) * 100
            seatbelt_compliance = max(0, (1 - no_seatbelt_count / total_violations)) * 100
            c1, c2 = st.columns(2)
            with c1:
                st.metric('Helmet Compliance', f"{helmet_compliance:.1f}%")
            with c2:
                st.metric('Seatbelt Compliance', f"{seatbelt_compliance:.1f}%")

            st.subheader('Violation Distribution')
            dist_df = pd.DataFrame({
                'Violation Type': ['NO HELMET', 'NO SEATBELT', 'TRIPLE RIDING'],
                'Count': [no_helmet_count, no_seatbelt_count, triple_riding_count],
            })
            try:
                import plotly.express as px
                fig3 = px.bar(dist_df, x='Violation Type', y='Count', title='Violation Distribution', color='Violation Type', color_discrete_sequence=px.colors.qualifier.Set2)
                st.plotly_chart(fig3, use_container_width=True)
            except ImportError:
                st.bar_chart(dist_df.set_index('Violation Type'))

elif page == PAGES[3]:
    st.header('Evaluation')

    st.subheader('Model Audit')
    model_path = 'models/traffic_violation_best.pt'
    model = load_model(model_path)
    st.write(f'**Model:** {model_path}')
    st.write(f'**Classes:** {model.names}')

    if st.button('Run Evaluation'):
        with st.spinner('Evaluating model...'):
            evaluator = ModelEvaluator(model_path)
            test_images = []
            for ext in ['*.jpg', '*.jpeg', '*.png']:
                test_images.extend([str(p) for p in Path('.').glob(ext)])
            if not test_images:
                import cv2 as _cv2
                import numpy as _np
                dummy = _np.ones((640, 640, 3), dtype=_np.uint8) * 128
                _cv2.imwrite('_eval_test.jpg', dummy)
                test_images = ['_eval_test.jpg']
            evaluator.evaluate(test_images)
            info = evaluator.summary()
            st.json(info)
            report_path = evaluator.export_report()
            with open(report_path) as f:
                st.markdown(f.read())
            if os.path.exists('_eval_test.jpg'):
                os.unlink('_eval_test.jpg')

elif page == PAGES[4]:
    st.header('Reports')

    init_db()
    rows = get_all_violations()
    stats = get_stats()

    if not rows:
        st.info('No data to generate reports. Save detections to database first.')
    else:
        st.subheader('Generate PDF Report')
        st.write(f'Total violations in database: {len(rows)}')
        if st.button('Generate Report'):
            with st.spinner('Generating PDF report...'):
                violations_list = [{'type': r['violation_type'], 'confidence': r['confidence'], 'plate_text': r.get('license_plate')} for r in rows]
                pdf_path = generate_pdf_report(violations_list, stats)
                with open(pdf_path, 'rb') as f:
                    st.download_button(
                        label='Download PDF Report',
                        data=f,
                        file_name=os.path.basename(pdf_path),
                        mime='application/pdf',
                    )
                st.success(f'Report generated: {pdf_path}')
