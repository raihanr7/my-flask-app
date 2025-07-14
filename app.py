from flask import Flask, jsonify, request, render_template
from flask_cors import CORS
import psycopg2
import json
import pytz
from datetime import datetime
from urllib.parse import unquote
import uuid

app = Flask(__name__)
CORS(app)

# Koneksi ke database PostgreSQL menggunakan Supabase pooler
conn = psycopg2.connect(
    host='aws-0-ap-southeast-1.pooler.supabase.com',  # Host dari Supabase pooler
    database='postgres',                               # Nama database
    user='postgres.wtmfsznnmyinbgzkdofz',             # Nama pengguna
    password='palaparingproject',                      # Ganti dengan password yang benar
    port='6543',                                       # Port untuk pooler
    options='-c timezone=Asia/Jakarta -c pool_mode=transaction'                     # Menentukan mode pool
)

FIELD_ORDER = {
    "Palapa_Ring_Barat_Alur": [
        "Link", "Project Name", "Project", "Panjang Kabel Laut", "Panjang Kabel Darat", "Total Panjang Kabel",
        "Kapasitas Palapa Ring", "Telkom Sewa", "Okupansi Telkom (%)", "Media Transmisi", "Periode", "Nilai Kontrak", "Updated at"
    ],
    "Palapa_Ring_Tengah_Alur": [
        "Link", "Project Name", "Project", "Panjang Kabel Laut", "Panjang Kabel Darat", "Total Panjang Kabel",
        "Kapasitas Palapa Ring", "Telkom Sewa", "Okupansi Telkom (%)", "Media Transmisi", "Periode", "Nilai Kontrak", "Updated at"
    ],
    "Palapa_Ring_Timur_Alur": [
        "Link", "Project Name", "Project", "Panjang Kabel Laut", "Panjang Kabel Darat", "Total Panjang Kabel",
        "Kapasitas Palapa Ring", "Telkom Sewa", "Okupansi Telkom (%)", "Media Transmisi", "Periode", "Nilai Kontrak", "Updated at"
    ],
    "Palapa_Ring_Barat_Point": [
        "Nama", "Project Name", "Project", "Nama Kota", "Nama Provinsi",
        "Longitude", "Latitude", "Keterangan", "Media Transmisi", "Nilai Kontrak", "Periode", "Updated at"
    ],
    "Palapa_Ring_Tengah_Point": [
        "Nama", "Project Name", "Project", "Nama Kota", "Nama Provinsi",
        "Longitude", "Latitude", "Keterangan", "Media Transmisi", "Nilai Kontrak", "Periode", "Updated at"
    ],
    "Palapa_Ring_Timur_Point": [
        "Nama", "Project Name","Project", "Nama Kota", "Nama Provinsi",
        "Longitude", "Latitude", "Keterangan", "Media Transmisi", "Nilai Kontrak", "Periode", "Updated at"
    ],
    "SubmarineCable_Alur": [
        "Link", "Description"
    ],

    "SKKL_Repair_2025_BY_DCS": [
        "name", "description"
    ],

    "SKKL_Repair_2024_BY_DCS": [
        "name", "description"
    ],

    "Backup Link": [
        "site", "description"
    ],

    "Link_Satelit": [
        "site", "description"
    ],
    
    "Palapa_Ring_FO_Cut": [
        "name","description"
    ]
}

def get_geojson_from_table(table_name):
    cur = conn.cursor()
    cur.execute(f'SELECT *, ST_AsGeoJSON(geom) FROM "{table_name}"')
    rows = cur.fetchall()
    colnames = [desc[0] for desc in cur.description]

    ordered_keys = FIELD_ORDER.get(table_name, colnames[:-1])
    wib_tz = pytz.timezone('Asia/Jakarta')

    features = []
    for i, row in enumerate(rows):
        try:
            full_props = dict(zip(colnames, row))
            # Konversi Updated at ke WIB jika ada
            if "Updated at" in full_props and full_props["Updated at"]:
                # full_props["Updated at"] adalah datetime aware (timestamptz)
                ts_utc = full_props["Updated at"]
                # convert ke WIB
                ts_wib = ts_utc.astimezone(wib_tz)
                # format ke string sesuai keinginan
                full_props["Updated at"] = ts_wib.strftime('%Y-%m-%d %H:%M:%S %Z')

            # Properties sesuai urutan
            props = {key: full_props.get(key, "") for key in ordered_keys}
            
            # Always include fid for update operations, even if not in display order
            if 'fid' in full_props and 'fid' not in props:
                props['fid'] = full_props['fid']

            if 'id' in full_props and 'id' not in props:
                props['id'] = full_props['id']

            if 'Project' in full_props and 'Project' not in props:
                props['Project'] = full_props['Project']
  
            # Check if we have geometry data
            if len(row) == 0:
                print(f"Warning: Empty row {i} in table {table_name}")
                continue
                
            geometry_json = row[-1]  # Last column should be the geometry
            if not geometry_json:
                print(f"Warning: No geometry data for row {i} in table {table_name}")
                continue

            feature = {
                "type": "Feature",
                "geometry": json.loads(geometry_json),
                "properties": props
            }
            features.append(feature)
            
        except Exception as e:
            print(f"Error processing row {i} in table {table_name}: {str(e)}")
            print(f"Row data: {row}")
            print(f"Column names: {colnames}")
            continue

    geojson = {
        "type": "FeatureCollection",
        "features": features,
        "field_order": ordered_keys
    }
    return geojson

def record_update_history(project_name, project, link_name, old_value, new_value):
    try:
        cur = conn.cursor()

        old_value_param = None if old_value in [None, '', 'None'] else float(old_value)
        new_value_param = None if new_value in [None, '', 'None'] else float(new_value)

        sql = '''
            INSERT INTO "Update History"
            ("Project Name", "Project", "Link Name", "Old Value", "New Value", "Updated at")
            VALUES (%s, %s, %s, %s, %s, NOW())
        '''
        cur.execute(sql, (project_name, project, link_name, old_value_param, new_value_param))

        conn.commit()
        cur.close()
        return True

    except Exception as e:
        print("DEBUG ERROR HISTORY INSERT:", str(e))
        conn.rollback()
        return False


# Rute untuk halaman utama (homepage)
@app.route('/')
def index():
    return render_template('Peta Palapa Ring Semi-Realtime.html')  # Menyajikan file HTML

# Endpoint GET data
@app.route('/api/point/barat')
def point_barat():
    return jsonify(get_geojson_from_table("Palapa_Ring_Barat_Point"))

@app.route('/api/alur/barat')
def alur_barat():
    return jsonify(get_geojson_from_table("Palapa_Ring_Barat_Alur"))

@app.route('/api/point/tengah')
def point_tengah():
    return jsonify(get_geojson_from_table("Palapa_Ring_Tengah_Point"))

@app.route('/api/alur/tengah')
def alur_tengah():
    return jsonify(get_geojson_from_table("Palapa_Ring_Tengah_Alur"))

@app.route('/api/point/timur')
def point_timur():
    return jsonify(get_geojson_from_table("Palapa_Ring_Timur_Point"))

@app.route('/api/alur/timur')
def alur_timur():
    return jsonify(get_geojson_from_table("Palapa_Ring_Timur_Alur"))

@app.route('/api/alur/submarine')
def alus_submarine():
    return jsonify(get_geojson_from_table("SubmarineCable_Alur"))

@app.route('/api/repair/skkl')
def repair_skkl():
    return jsonify(get_geojson_from_table("SKKL_Repair_2025_BY_DCS"))

@app.route('/api/fo-cut/paring')
def fo_cut_paring():
    return jsonify(get_geojson_from_table("Palapa_Ring_FO_Cut"))


@app.route('/api/repair/skkl2024')
def repair_skkl2024():
    return jsonify(get_geojson_from_table("SKKL_Repair_2024_BY_DCS"))

@app.route('/api/backup-link')
def backup_link():
    return jsonify(get_geojson_from_table("Backup Link"))

@app.route('/api/link-satelit')
def link_satelit():
    return jsonify(get_geojson_from_table("Link_Satelit"))

@app.route('/api/tambah-marker', methods=['POST'])
def tambah_marker():
    data = request.json
    kategori = data.get('kategori')
    lat, lng = data.get('lat'), data.get('lng')
    site = data.get('site')
    description = data.get('description')
    new_id = uuid.uuid4().hex.upper()  # Selalu generate UUID

    if kategori == 'backup':
        table_name = "Backup Link"
        field_name = "site"
    elif kategori == 'linksatelit':
        table_name = "Link_Satelit"
        field_name = "site"
    elif kategori == 'repair2024':
        table_name = "SKKL_Repair_2024_BY_DCS"
        field_name = "name"
    elif kategori == 'repair2025':
        table_name = "SKKL_Repair_2025_BY_DCS"
        field_name = "name"
    elif kategori == 'fo_cut':                       
        table_name = "Palapa_Ring_FO_Cut"
        field_name = "name"
    else:
        return {"success": False, "error": "Kategori tidak dikenal"}, 400

    try:
        cur = conn.cursor()
        geom_wkt = f"POINT({lng} {lat})"
        # SEMUA tabel diinsert kolom id, field_name, description, geom
        sql = f'INSERT INTO "{table_name}" ("id", "{field_name}", "description", "geom") VALUES (%s, %s, %s, ST_GeomFromText(%s, 4326))'
        cur.execute(sql, (new_id, site, description, geom_wkt))
        conn.commit()
        cur.close()
        return {"success": True}
    except Exception as e:
        conn.rollback()
        return {"success": False, "error": str(e)}, 500

@app.route('/api/delete-marker', methods=['POST'])
def delete_marker():
    data = request.json
    kategori = data.get('kategori')
    marker_id = data.get('id')
    if not kategori or not marker_id:
        return {"success": False, "error": "Invalid data"}, 400

    if kategori == 'backup':
        table_name = "Backup Link"
    elif kategori == 'linksatelit':
        table_name = "Link_Satelit"
    elif kategori == 'repair2024':
        table_name = "SKKL_Repair_2024_BY_DCS"
    elif kategori == 'repair2025':
        table_name = "SKKL_Repair_2025_BY_DCS"
    elif kategori == 'fo_cut':
        table_name = "Palapa_Ring_FO_Cut"
    else:
        return {"success": False, "error": "Kategori tidak dikenal"}, 400

    try:
        cur = conn.cursor()
        print('HAPUS MARKER:', table_name, marker_id)
        sql = f'DELETE FROM "{table_name}" WHERE id=%s'
        cur.execute(sql, (marker_id,))
        print('ROWCOUNT:', cur.rowcount)
        conn.commit()
        cur.close()
        return {"success": True}
    except Exception as e:
        conn.rollback()
        return {"success": False, "error": str(e)}, 500


@app.route('/api/update-marker', methods=['POST'])
def update_marker():
    data = request.json
    kategori = data.get('kategori')
    marker_id = data.get('id')
    lat, lng = data.get('lat'), data.get('lng')

    if not (kategori and marker_id and lat and lng):
        return {"success": False, "error": "Incomplete data"}, 400

    table_map = {
        'backup': 'Backup Link',
        'linksatelit': 'Link_Satelit',
        'repair2024': 'SKKL_Repair_2024_BY_DCS',
        'repair2025': 'SKKL_Repair_2025_BY_DCS',
        'fo_cut': 'Palapa_Ring_FO_Cut'
    }
    table_name = table_map.get(kategori)
    if not table_name:
        return {"success": False, "error": "Kategori tidak dikenal"}, 400

    try:
        cur = conn.cursor()
        # Update kolom geom dengan titik baru
        sql = f'''UPDATE "{table_name}"
                  SET geom = ST_SetSRID(ST_MakePoint(%s, %s), 4326)
                  WHERE id = %s'''
        cur.execute(sql, (lng, lat, marker_id))
        conn.commit()
        cur.close()
        return {"success": True}
    except Exception as e:
        conn.rollback()
        return {"success": False, "error": str(e)}, 500

@app.route('/api/update-okupansi', methods=['POST'])
def update_okupansi():
    data = request.json or {}
    kategori = data.get('kategori')     
    scope    = data.get('scope')        
    value    = data.get('value')        
    link_name = data.get('link_name', '').strip()
    project   = data.get('project')

    table_map = {
        'barat':  'Palapa_Ring_Barat_Alur',
        'tengah': 'Palapa_Ring_Tengah_Alur',
        'timur':  'Palapa_Ring_Timur_Alur'
    }

    table = table_map.get(kategori)
    if not table:
        return {"success": False, "error": "Kategori tidak valid"}, 400
    if scope not in ('link', 'project'):
        return {"success": False, "error": "Scope tidak valid"}, 400
    if value is None:
        return {"success": False, "error": "Value kosong"}, 400

    try:
        with conn.cursor() as cur:

            if scope == 'link':
                sql = '''
                    SELECT "Okupansi Telkom (%%)", "Project", "Link"
                    FROM "{}"
                    WHERE TRIM("Link") = %s
                    LIMIT 1
                '''.format(table)
                cur.execute(sql, (link_name,))
                result = cur.fetchone()
                print("DEBUG RESULT:", result)

                if not result or len(result) < 3:
                    return {"success": False, "error": f'Data untuk link "{link_name}" tidak ditemukan'}, 404

                old_value, project_code, link_from_db = result

                project_name = {
                    'barat': 'Palapa Ring Barat',
                    'tengah': 'Palapa Ring Tengah',
                    'timur': 'Palapa Ring Timur'
                }.get(kategori, 'Unknown')

                sql_update = '''
                    UPDATE "{}"
                    SET "Okupansi Telkom (%%)" = %s, "Updated at" = NOW()
                    WHERE TRIM("Link") = %s
                '''.format(table)
                cur.execute(sql_update, (value, link_name))

                record_update_history(
                    project_name=project_name,
                    project=project_code,
                    link_name=link_from_db,
                    old_value=old_value,
                    new_value=value
                )


            elif scope == 'project':
                # 1. Ambil nama project_name berdasarkan kode project
                sql = f'''
                    SELECT DISTINCT "Project Name"
                    FROM "{table}"
                    WHERE "Project" = %s
                    LIMIT 1
                '''
                cur.execute(sql, (project,))
                result = cur.fetchone()

                if not result or not result[0]:
                    return {"success": False, "error": f'Project Name tidak ditemukan untuk project "{project}"'}, 404

                project_name = result[0]

                # 2. Update semua link dalam satu project
                sql_update = f'''
                    UPDATE "{table}"
                    SET "Okupansi Telkom (%%)" = %s, "Updated at" = NOW()
                    WHERE "Project" = %s
                '''
                cur.execute(sql_update, (value, project))

                if cur.rowcount == 0:
                    return {"success": False, "error": f'Tidak ada data untuk project "{project}"'}, 404

                # 3. Catat ke histori
                record_update_history(
                    project_name=project_name,
                    project=project,
                    link_name='Seluruh Project',
                    old_value=None,
                    new_value=value
                )

        conn.commit()
        return {"success": True}

    except Exception as e:
        conn.rollback()
        import traceback
        traceback.print_exc()
        return {"success": False, "error": str(e)}, 500



# âœ¨ Endpoint dinamis untuk update data dan "Updated at"
@app.route('/api/update/<table_name>/<int:fid>', methods=['POST'])
def update_table(table_name, fid):
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "No data provided"}), 400

        # Get current values before update if Okupansi is being changed
        old_value = None
        project_name = None
        link_name = None
        
        if "Okupansi Telkom (%)" in data:
            try:
                cur = conn.cursor()
                # Check if required columns exist first
                cur.execute("""
                    SELECT column_name 
                    FROM information_schema.columns 
                    WHERE table_schema = 'public' AND table_name = %s
                    AND column_name IN ('Okupansi Telkom (%)', 'Project', 'Link')
                """, (table_name,))
                available_cols = [row[0] for row in cur.fetchall()]
                
                # Build query based on available columns
                select_cols = []
                if 'Okupansi Telkom (%)' in available_cols:
                    select_cols.append('"Okupansi Telkom (%)"')
                if 'Project' in available_cols:
                    select_cols.append('"Project"')
                if 'Link' in available_cols:
                    select_cols.append('"Link"')
                
                if select_cols:
                    cur.execute(f'SELECT {", ".join(select_cols)} FROM "{table_name}" WHERE fid = %s', (fid,))
                    result = cur.fetchone()
                    
                    if result:
                        col_index = 0
                        if 'Okupansi Telkom (%)' in available_cols:
                            old_value = result[col_index] if result[col_index] is not None else None
                            col_index += 1
                        if 'Project' in available_cols:
                            project_name = result[col_index] if col_index < len(result) and result[col_index] is not None else "Unknown Project"
                            col_index += 1
                        if 'Link' in available_cols:
                            link_name = result[col_index] if col_index < len(result) and result[col_index] is not None else f"FID-{fid}"
                        
                        # Set defaults if not found
                        if project_name is None:
                            project_name = "Unknown Project"
                        if link_name is None:
                            link_name = f"FID-{fid}"
                        
                        print(f"DEBUG: Found existing values for fid {fid}: old_value={old_value}, project={project_name}, link={link_name}")
                    else:
                        print(f"DEBUG: No existing values found for fid {fid}")
                        project_name = "Unknown Project"
                        link_name = f"FID-{fid}"
                        
                cur.close()
            except Exception as query_error:
                print(f"DEBUG: Error querying existing values: {str(query_error)}")
                project_name = "Unknown Project"
                link_name = f"FID-{fid}"

        # Prepare update query
        set_clauses = []
        values = []
        for key, value in data.items():
            set_clauses.append(f'"{key}" = %s')
            values.append(value)

        # Add Updated at = NOW()
        set_clauses.append('"Updated at" = NOW()')

        # Execute update query
        sql = f'UPDATE "{table_name}" SET {", ".join(set_clauses)} WHERE fid = %s'
        values.append(fid)

        cur = conn.cursor()
        cur.execute(sql, tuple(values))
        affected_rows = cur.rowcount
        conn.commit()
        cur.close()
        
        # Record history if Okupansi was changed and update was successful
        if "Okupansi Telkom (%)" in data and affected_rows > 0:
            new_value = data["Okupansi Telkom (%)"]
            history_success = record_update_history(
                project_name=project_name,
                link_name=link_name,
                old_value=old_value,
                new_value=new_value
            )
            if not history_success:
                print("WARNING: Failed to record history, but main update succeeded")
        
        if affected_rows == 0:
            return jsonify({"error": f"No record found with fid {fid} in table {table_name}"}), 404
            
        return jsonify({
            "message": f"Table {table_name} fid {fid} updated successfully", 
            "affected_rows": affected_rows,
            "history_recorded": "Okupansi Telkom (%)" in data
        })
    
    except Exception as e:
        try:
            conn.rollback()
        except:
            pass
            
        print(f"DEBUG: Exception in update_table: {str(e)}")
        import traceback
        traceback.print_exc()
        
        return jsonify({"error": f"Database error: {str(e)}"}), 500

# ✅ FIXED Alternative endpoint for alur tables using Link field
@app.route('/api/update-by-link/<table_name>/<path:link>', methods=['POST'])
def update_table_by_link(table_name, link):
    # PERBAIKAN: Decode URL untuk mengubah %20 menjadi spasi, dll.
    decoded_link = unquote(link)

    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "No data provided"}), 400

        cur = conn.cursor()

        # STEP 1: Find the FID using the decoded link name.
        # Menggunakan decoded_link untuk membersihkan nama link
        link_cleaned = " ".join(decoded_link.strip().split())
        find_fid_sql = f'SELECT "fid" FROM "{table_name}" WHERE TRIM("Link") = %s LIMIT 1'
        print(f"DEBUG STEP 1: Finding FID with query: {find_fid_sql} and params: ('{link_cleaned}',)")
        
        cur.execute(find_fid_sql, (link_cleaned,))
        result_fid = cur.fetchone()

        if not result_fid:
            cur.close()
            return jsonify({"error": f"No record found with Link matching '{link_cleaned}'"}), 404
        
        # We found the FID!
        fid = result_fid[0]
        print(f"DEBUG STEP 1 SUCCESS: Found fid: {fid}")

        # STEP 2: Get old values using the reliable FID.
        get_old_values_sql = f'SELECT "Okupansi Telkom (%%)", "Project Name", "Project", "Link" FROM "{table_name}" WHERE "fid" = %s'
        print(f"DEBUG STEP 2: Getting old values with query: {get_old_values_sql} and params: ({fid},)")
        
        cur.execute(get_old_values_sql, (fid,))
        old_values_result = cur.fetchone()
        
        if not old_values_result:
            # This should ideally never happen if we just found the fid
            cur.close()
            return jsonify({"error": f"Inconsistency: Found fid {fid} but could not retrieve its data."}), 500

        old_value, project_name, project, link_name_from_db = old_values_result
        print(f"DEBUG STEP 2 SUCCESS: Old Value={old_value}, Project Name ={project_name}, Project={project}, Link={link_name_from_db}")
        
        # STEP 3: Perform the final update using the reliable FID.
        new_okupansi = float(data['Okupansi Telkom (%)'])
        update_sql = f'UPDATE "{table_name}" SET "Okupansi Telkom (%%)" = %s, "Updated at" = NOW() WHERE "fid" = %s'
        print(f"DEBUG STEP 3: Updating with query: {update_sql} and params: ({new_okupansi}, {fid})")
        
        cur.execute(update_sql, (new_okupansi, fid))
        affected_rows = cur.rowcount
        conn.commit()

        # STEP 4: Record history.
        if affected_rows > 0:
            print("DEBUG STEP 4: Recording history.")
            record_update_history(
                project_name=project_name,
                project = project,
                link_name=link_name_from_db,
                old_value=old_value,
                new_value=new_okupansi
            )

        cur.close()
        return jsonify({
            "message": f"Update successful for Link '{link_name_from_db}' (fid: {fid})",
            "affected_rows": affected_rows
        })

    except Exception as e:
        import traceback
        traceback.print_exc()
        try:
            conn.rollback()
        except:
            pass
        return jsonify({"error": f"An internal server error occurred: {str(e)}"}), 500

@app.route('/api/update-history', methods=['GET'])
def get_update_history():
    try:
        project_name = request.args.get('project name')
        project = request.args.get('project')
        link_name = request.args.get('link')
        limit = request.args.get('limit', default=100, type=int)
        
        cur = conn.cursor()
        
        query = '''
            SELECT "History ID", "Project Name", "Project, "Link Name", "Old Value", "New Value", "Updated at"
            FROM "Update History"
            WHERE 1=1
        '''
        params = []
        
        if project_name:
            query += ' AND "Project Name" = %s'
            params.append(project_name)

        if project:
            query += ' AND "Project" = %s'
            params.append(project)    
        
        if link_name:
            query += ' AND "Link Name" = %s'
            params.append(link_name)
        
        query += ' ORDER BY "Updated at" DESC LIMIT %s'
        params.append(limit)
        
        cur.execute(query, params)
        columns = [desc[0] for desc in cur.description]
        
        wib_tz = pytz.timezone('Asia/Jakarta')
        
        history_data = []
        for row in cur.fetchall():
            history_item = {}
            for i, column in enumerate(columns):
                if column == "Updated at" and row[i] is not None:
                    ts_utc = row[i]
                    ts_wib = ts_utc.astimezone(wib_tz)
                    history_item[column] = ts_wib.strftime('%Y-%m-%d %H:%M:%S %Z')
                else:
                    history_item[column] = row[i]
            history_data.append(history_item)
        
        cur.close()
        return jsonify({"data": history_data})
    
    except Exception as e:
        print(f"Error retrieving update history: {e}")
        import traceback
        traceback.print_exc()
        
        return jsonify({"error": str(e)}), 500

@app.route('/api/setup-history-table', methods=['GET'])
def setup_history_table():
    try:
        # SOLUSI: Membersihkan transaksi yang mungkin 'macet' dari request sebelumnya
        conn.rollback()

        cur = conn.cursor()
        
        # Check if the table already exists (Logika Anda di sini sudah benar)
        cur.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_name = 'Update History'
            )
        """)
        table_exists = cur.fetchone()[0]
        
        if table_exists:
            cur.close()
            return jsonify({"status": "Already exists", "message": "Update History table already exists"})
        
        # Create the table (Logika Anda di sini sudah benar)
        create_table_sql = """
            CREATE TABLE "Update History" (
                "History ID" SERIAL PRIMARY KEY,
                "Project Name" VARCHAR(255),
                "Link Name" VARCHAR(255),
                "Old Value" NUMERIC,
                "New Value" NUMERIC,
                "Updated at" TIMESTAMP WITH TIME ZONE DEFAULT NOW()
            )
        """
        
        cur.execute(create_table_sql)
        conn.commit()
        cur.close()
        
        return jsonify({
            "status": "Created",
            "message": "Update History table created successfully"
        })
        
    except Exception as e:
        # Blok penanganan error Anda sudah bagus
        try:
            conn.rollback()
        except:
            pass
            
        error_msg = str(e)
        print(f"DEBUG: Exception in setup_history_table: {error_msg}")
        
        return jsonify({
            "status": "Error",
            "message": f"Failed to create table: {error_msg}"
        }), 500

# Ganti fungsi @app.route('/history') yang lama dengan yang ini di app.py


@app.route('/history')
def history():
    try:
        cur = conn.cursor()
        selected_project_name = request.args.get('project_name_filter', '')
        selected_project = request.args.get('project_filter', '')

        # PAGINATION
        page = request.args.get('page', default=1, type=int)
        per_page = 20
        offset = (page - 1) * per_page

        cur.execute('SELECT DISTINCT "Project Name" FROM "Update History" WHERE "Project Name" IS NOT NULL ORDER BY "Project Name";')
        project_names = [row[0] for row in cur.fetchall()]

        cur.execute('SELECT DISTINCT "Project" FROM "Update History" WHERE "Project" IS NOT NULL ORDER BY "Project";')
        projects = [row[0] for row in cur.fetchall()]

        params = []
        conditions = []
        query_count = '''
            SELECT COUNT(*) FROM "Update History"
        '''
        query = '''
            SELECT "History ID", "Project Name", "Project", "Link Name", "Old Value", "New Value", "Updated at"
            FROM "Update History"
        '''

        if selected_project_name:
            conditions.append('"Project Name" = %s')
            params.append(selected_project_name)
        if selected_project:
            conditions.append('"Project" = %s')
            params.append(selected_project)
        if conditions:
            query += ' WHERE ' + ' AND '.join(conditions)
            query_count += ' WHERE ' + ' AND '.join(conditions)
        query += ' ORDER BY "Updated at" DESC LIMIT %s OFFSET %s;'
        params_count = params.copy()  # jangan lupa untuk count juga
        params.append(per_page)
        params.append(offset)

        # Hitung total data untuk pagination
        cur.execute(query_count, tuple(params_count))
        total_data = cur.fetchone()[0]
        total_pages = max(1, -(-total_data // per_page))  # pembulatan ke atas

        cur.execute(query, tuple(params))
        columns = [desc[0] for desc in cur.description]
        history_data_raw = cur.fetchall()
        cur.close()

        import pytz
        wib_tz = pytz.timezone('Asia/Jakarta')
        history_data = []
        for row in history_data_raw:
            item = dict(zip(columns, row))
            if item.get("Updated at"):
                item["Updated at"] = item["Updated at"].astimezone(wib_tz).strftime('%Y-%m-%d %H:%M:%S %Z')
            history_data.append(item)

        return render_template(
            'history.html',
            history_data=history_data,
            project_names=project_names,
            projects=projects,
            selected_project_name=selected_project_name,
            selected_project=selected_project,
            page=page,
            total_pages=total_pages
        )

    except Exception as e:
        import traceback
        traceback.print_exc()
        return "Gagal memuat riwayat. Silakan cek terminal untuk detail error."


# Debug endpoints
@app.route('/api/debug/table/<table_name>')
def debug_table_structure(table_name):
    try:
        cur = conn.cursor()
        cur.execute(f'SELECT column_name, data_type FROM information_schema.columns WHERE table_name = %s ORDER BY ordinal_position', (table_name,))
        columns = cur.fetchall()
        cur.close()
        return jsonify({
            "table": table_name,
            "columns": [{"name": col[0], "type": col[1]} for col in columns]
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/debug/test/<table_name>')
def debug_test_table(table_name):
    try:
        cur = conn.cursor()
        
        # Test basic select
        cur.execute(f'SELECT COUNT(*) FROM "{table_name}"')
        count_result = cur.fetchone()
        total_rows = count_result[0] if count_result else 0
        
        # Test select with columns
        cur.execute(f'SELECT * FROM "{table_name}" LIMIT 1')
        sample_row = cur.fetchone()
        colnames = [desc[0] for desc in cur.description]
        
        cur.close()
        
        return jsonify({
            "table": table_name,
            "total_rows": total_rows,
            "column_count": len(colnames),
            "columns": colnames,
            "sample_row_length": len(sample_row) if sample_row else 0,
            "has_geometry": "geom" in colnames,
            "status": "success"
        })
    except Exception as e:
        return jsonify({
            "table": table_name,
            "error": str(e),
            "status": "error"
        }), 500

@app.route('/api/debug/links/<table_name>')
def debug_links(table_name):
    try:
        cur = conn.cursor()
        
        # Get all Link values
        cur.execute(f'SELECT "Link", "Okupansi Telkom (%)" FROM "{table_name}" LIMIT 10')
        links = cur.fetchall()
        
        cur.close()
        
        return jsonify({
            "table": table_name,
            "links": [{"link": row[0], "okupansi": row[1]} for row in links] if links else [],
            "count": len(links) if links else 0
        })
    except Exception as e:
        return jsonify({
            "table": table_name,
            "error": str(e)
        }), 500

@app.route('/api/debug/history')
def debug_history_table():
    try:
        cur = conn.cursor()
        
        cur.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_name = 'Update History'
            )
        """)
        table_exists = cur.fetchone()[0]
        
        result = {
            "table_exists": table_exists
        }
        
        if table_exists:
            cur.execute("""
                SELECT column_name, data_type
                FROM information_schema.columns
                WHERE table_name = 'Update History'
                ORDER BY ordinal_position
            """)
            columns = cur.fetchall()
            result["columns"] = [{"name": col[0], "type": col[1]} for col in columns]
            
            cur.execute('SELECT COUNT(*) FROM "Update History"')
            count = cur.fetchone()[0]
            result["record_count"] = count
            
            cur.execute('SELECT * FROM "Update History" ORDER BY "Updated at" DESC LIMIT 5')
            sample_rows = cur.fetchall()
            column_names = [desc[0] for desc in cur.description]
            
            sample_data = []
            for row in sample_rows:
                row_dict = {}
                for i, col in enumerate(column_names):
                    if col == "Updated at" and row[i] is not None:
                        row_dict[col] = row[i].isoformat()
                    else:
                        row_dict[col] = row[i]
                sample_data.append(row_dict)
            
            result["sample_data"] = sample_data
        
        cur.close()
        return jsonify(result)
    except Exception as e:
        return jsonify({
            "error": str(e),
            "table_exists": False
        }), 500

# Menjalankan server
if __name__ == '__main__':
    app.run(debug=True)