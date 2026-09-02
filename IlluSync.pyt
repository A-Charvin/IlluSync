import arcpy
import string
import re

class Toolbox(object):
    def __init__(self):
        self.label = "IlluSync Tools"
        self.alias = "illusync"
        self.tools = [IlluSync]

class IlluSync(object):
    def __init__(self):
        self.label = "IlluSync Address QC"
        self.description = "Validates civic points against parcel polygons."
        self.canRunInBackground = True

    def getParameterInfo(self):
        p_parcels = arcpy.Parameter(
            displayName="Parcel Layer",
            name="parcel_lyr",
            datatype="GPFeatureLayer",
            parameterType="Required",
            direction="Input")
        p_parcels.filter.list = ["Polygon"]

        p_arn = arcpy.Parameter(
            displayName="Parcel ARN Field",
            name="parcel_arn",
            datatype="Field",
            parameterType="Required",
            direction="Input")
        p_arn.parameterDependencies = [p_parcels.name]
        p_arn.filter.list = ["Text", "Short", "Long", "OID", "Double"]

        p_addr = arcpy.Parameter(
            displayName="Parcel Address Field",
            name="parcel_addr",
            datatype="Field",
            parameterType="Required",
            direction="Input")
        p_addr.parameterDependencies = [p_parcels.name]
        p_addr.filter.list = ["Text"]

        p_civic = arcpy.Parameter(
            displayName="Civic Point Layer",
            name="civic_lyr",
            datatype="GPFeatureLayer",
            parameterType="Required",
            direction="Input")
        p_civic.filter.list = ["Point"]

        c_arn = arcpy.Parameter(
            displayName="Civic ARN Field",
            name="civic_arn",
            datatype="Field",
            parameterType="Required",
            direction="Input")
        c_arn.parameterDependencies = [p_civic.name]
        c_arn.filter.list = ["Text", "Short", "Long", "OID", "Double"]

        c_addr = arcpy.Parameter(
            displayName="Civic Address Field",
            name="civic_addr",
            datatype="Field",
            parameterType="Required",
            direction="Input")
        c_addr.parameterDependencies = [p_civic.name]
        c_addr.filter.list = ["Text"]

        p_out = arcpy.Parameter(
            displayName="Output Exception Feature Class",
            name="output_fc",
            datatype="DEFeatureClass",
            parameterType="Required",
            direction="Output")

        return [p_parcels, p_arn, p_addr, p_civic, c_arn, c_addr, p_out]

    def updateParameters(self, parameters):
        return

    def execute(self, parameters, messages):
        messages.addMessage("Starting IlluSync validation...")
        arcpy.env.workspace = "memory"
        arcpy.env.overwriteOutput = True

        parcel_lyr = parameters[0].valueAsText
        p_arn_fld = parameters[1].valueAsText
        p_addr_fld = parameters[2].valueAsText
        civic_lyr = parameters[3].valueAsText
        c_arn_fld = parameters[4].valueAsText
        c_addr_fld = parameters[5].valueAsText
        out_fc = parameters[6].valueAsText

        arcpy.env.outputCoordinateSystem = arcpy.Describe(parcel_lyr).spatialReference

        def normalize_text(text):
            if not text:
                return ""
            text = str(text).lower()
            text = re.sub(r'[\s-]*\bwao\b', '', text)
            text = text.translate(str.maketrans("", "", string.punctuation))

            suffix_map = {
                r'\brd\b': 'road', r'\bst\b': 'street', r'\bave\b': 'avenue',
                r'\bblvd\b': 'boulevard', r'\bdr\b': 'drive', r'\bcres\b': 'crescent',
                r'\bcrt\b': 'court', r'\bpl\b': 'place', r'\bter\b': 'terrace',
                r'\bhwy\b': 'highway', r'\bln\b': 'lane', r'\bcir\b': 'circle',
                r'\btr\b': 'trail', r'\bpkwy\b': 'parkway',
                r'\bn\b': 'north', r'\bs\b': 'south', r'\be\b': 'east', r'\bw\b': 'west',
                r'\bne\b': 'northeast', r'\bnw\b': 'northwest',
                r'\bse\b': 'southeast', r'\bsw\b': 'southwest'
            }

            for pattern, replacement in suffix_map.items():
                text = re.sub(pattern, replacement, text)

            text = re.sub(r"\s+", " ", text).strip()
            return text

        def is_civic_address(text):
            if not text:
                return False

            words = text.split()
            if not words:
                return False

            first_word = words[0]

            if not first_word.isdigit():
                return False

            if len(first_word) >= 3:
                return True

            if len(words) > 1:
                second_word = words[1]
                rural_indicators = {
                    'line', 'highway', 'hwy', 'con', 'concession',
                    'route', 'rte', 'sideroad'
                }
                if second_word in rural_indicators:
                    return False

            return True

        def truncate_text(text, max_len):
            if not text:
                return ""
            text = str(text)
            if len(text) <= max_len:
                return text
            return text[:max_len - 3] + "..."

        def add_field_map(field_mappings, source_layer, source_field, output_name):
            fm = arcpy.FieldMap()
            fm.addInputField(source_layer, source_field)
            out_field = fm.outputField
            out_field.name = output_name
            fm.outputField = out_field
            field_mappings.addFieldMap(fm)

        messages.addMessage("Performing spatial join...")
        join_out = "memory/parcel_join"

        civic_desc = arcpy.Describe(civic_lyr)
        civic_oid_field = civic_desc.OIDFieldName

        field_mappings = arcpy.FieldMappings()
        add_field_map(field_mappings, parcel_lyr, p_arn_fld, "P_ARN_J")
        add_field_map(field_mappings, parcel_lyr, p_addr_fld, "P_ADR_J")
        add_field_map(field_mappings, civic_lyr, civic_oid_field, "C_OID_J")
        add_field_map(field_mappings, civic_lyr, c_arn_fld, "C_ARN_J")
        add_field_map(field_mappings, civic_lyr, c_addr_fld, "C_ADR_J")

        arcpy.analysis.SpatialJoin(
            parcel_lyr,
            civic_lyr,
            join_out,
            "JOIN_ONE_TO_MANY",
            "KEEP_ALL",
            field_mappings
        )

        join_fields = [f.name for f in arcpy.ListFields(join_out)]

        if "TARGET_FID" in join_fields:
            target_id_field = "TARGET_FID"
        elif "P_ARN_J" in join_fields:
            target_id_field = "P_ARN_J"
        else:
            target_id_field = "OID"

        point_count = {}
        point_summary = {}

        messages.addMessage("Building civic point count per parcel...")

        if "C_OID_J" in join_fields:
            summary_fields = [target_id_field, "C_OID_J", "C_ARN_J", "C_ADR_J"]

            with arcpy.da.SearchCursor(join_out, summary_fields) as cursor:
                for row in cursor:
                    target_id = row[0]
                    civic_oid = row[1]

                    if civic_oid is not None:
                        point_count[target_id] = point_count.get(target_id, 0) + 1

                        c_arn_summary = str(row[2]).strip() if row[2] is not None else ""
                        c_addr_summary = str(row[3]).strip() if row[3] is not None else ""

                        if c_arn_summary or c_addr_summary:
                            entry = f"ARN:{c_arn_summary} ADD:{c_addr_summary}"
                            point_summary.setdefault(target_id, []).append(entry)

        else:
            summary_fields = [target_id_field, "C_ARN_J", "C_ADR_J"]

            with arcpy.da.SearchCursor(join_out, summary_fields) as cursor:
                for row in cursor:
                    target_id = row[0]
                    c_arn_summary = str(row[1]).strip() if row[1] is not None else ""
                    c_addr_summary = str(row[2]).strip() if row[2] is not None else ""

                    if c_arn_summary or c_addr_summary:
                        point_count[target_id] = point_count.get(target_id, 0) + 1
                        entry = f"ARN:{c_arn_summary} ADD:{c_addr_summary}"
                        point_summary.setdefault(target_id, []).append(entry)

        parcel_errors = {}

        def get_parcel_record(target_id, geom, p_arn, p_addr_raw, parcel_point_count):
            if target_id not in parcel_errors:
                parcel_errors[target_id] = {
                    "SHAPE@": geom,
                    "P_ARN": p_arn,
                    "P_ADDR": p_addr_raw,
                    "PT_COUNT": parcel_point_count,
                    "C_LIST": truncate_text("; ".join(point_summary.get(target_id, [])), 250),
                    "NOTE": "MULTI POINT" if parcel_point_count > 1 else "",
                    "POINT_ERRORS": [],
                    "SEEN_ERRORS": set()
                }

            return parcel_errors[target_id]

        messages.addMessage("Evaluating parcel and civic attributes...")

        fields = [
            target_id_field,
            "SHAPE@",
            "P_ARN_J",
            "P_ADR_J",
            "C_ARN_J",
            "C_ADR_J"
        ]

        with arcpy.da.SearchCursor(join_out, fields) as cursor:
            for row in cursor:
                target_id = row[0]
                poly_geom = row[1]

                p_arn = str(row[2]).strip() if row[2] is not None else ""
                p_addr_raw = row[3] if row[3] is not None else ""
                p_addr = normalize_text(p_addr_raw)

                c_arn = str(row[4]).strip() if row[4] is not None else ""
                c_addr_raw = row[5] if row[5] is not None else ""
                c_addr = normalize_text(c_addr_raw)

                parcel_point_count = point_count.get(target_id, 0)

                rec = get_parcel_record(
                    target_id,
                    poly_geom,
                    p_arn,
                    p_addr_raw,
                    parcel_point_count
                )

                parcel_is_specific = is_civic_address(p_addr)
                civic_is_specific = is_civic_address(c_addr)

                if parcel_point_count == 0:
                    if parcel_is_specific:
                        err_key = ("", "", "E01_MISS_PT")
                        if err_key not in rec["SEEN_ERRORS"]:
                            rec["SEEN_ERRORS"].add(err_key)
                            rec["POINT_ERRORS"].append({
                                "C_ARN": "",
                                "C_ADDR": "",
                                "SPAT_STS": "MISSING",
                                "MATCH_TYP": "FAIL",
                                "ERR_CODE": "E01_MISS_PT",
                                "ERR_DESC": "Parcel has specific address but no civic point"
                            })
                    continue

                if not c_arn and not c_addr:
                    continue

                err_code = ""
                err_desc = ""
                match_typ = ""
                spat_sts = "INSIDE"

                if c_arn == p_arn and not c_addr:
                    err_code = "E09_GHOST"
                    err_desc = "Civic point exists with ARN but no address"
                    match_typ = "FAIL"
                    spat_sts = "GHOST"

                elif c_arn != p_arn:
                    err_code = "E05_ARN_MIS"
                    err_desc = "ARN mismatch"
                    match_typ = "FAIL"

                elif c_addr == p_addr:
                    continue

                elif civic_is_specific and not parcel_is_specific:
                    err_code = "E10_PADDR"
                    err_desc = "Civic has valid address but parcel address is missing or invalid"
                    match_typ = "FAIL"

                elif not parcel_is_specific:
                    continue

                elif c_addr and p_addr and (c_addr in p_addr or p_addr in c_addr):
                    err_code = "E08_PARTIAL"
                    err_desc = "Partial address match"
                    match_typ = "PARTIAL"

                else:
                    err_code = "E06_ADDR_MIS"
                    err_desc = "Complete address mismatch"
                    match_typ = "FAIL"

                if err_code:
                    err_key = (c_arn, c_addr, err_code)
                    if err_key not in rec["SEEN_ERRORS"]:
                        rec["SEEN_ERRORS"].add(err_key)
                        rec["POINT_ERRORS"].append({
                            "C_ARN": c_arn,
                            "C_ADDR": c_addr_raw,
                            "SPAT_STS": spat_sts,
                            "MATCH_TYP": match_typ,
                            "ERR_CODE": err_code,
                            "ERR_DESC": err_desc
                        })

        messages.addMessage("Checking for orphaned civic points...")
        arcpy.management.MakeFeatureLayer(civic_lyr, "civic_mem")
        arcpy.management.SelectLayerByLocation(
            "civic_mem",
            "INTERSECT",
            parcel_lyr,
            "",
            "NEW_SELECTION",
            "INVERT"
        )

        orphan_count = int(arcpy.management.GetCount("civic_mem")[0])
        orphan_buff = "memory/orphan_buff"

        if orphan_count > 0:
            messages.addMessage(f"Found {orphan_count} orphaned points. Buffering for polygon output...")

            sr = arcpy.Describe(civic_lyr).spatialReference
            buff_dist = "0.00001" if sr.type == "Geographic" else "1"

            arcpy.analysis.Buffer("civic_mem", orphan_buff, buff_dist)

            miss_fields = ["SHAPE@", c_arn_fld, c_addr_fld]
            with arcpy.da.SearchCursor(orphan_buff, miss_fields) as cursor:
                for row in cursor:
                    c_arn_orphan = str(row[1]).strip() if row[1] is not None else ""
                    c_addr_orphan = row[2] if row[2] is not None else ""

                    orphan_list = truncate_text(
                        f"ARN:{c_arn_orphan} ADD:{str(c_addr_orphan).strip()}",
                        250
                    )

                    orphan_err_list = truncate_text(
                        f"{c_arn_orphan}|{str(c_addr_orphan).strip()}|E02_ORPHAN",
                        250
                    )

                    parcel_errors[f"ORPHAN_{c_arn_orphan}_{str(c_addr_orphan).strip()}_{row[0].WKT}"] = {
                        "SHAPE@": row[0],
                        "P_ARN": "",
                        "P_ADDR": "",
                        "PT_COUNT": 1,
                        "C_LIST": orphan_list,
                        "NOTE": "ORPHAN",
                        "POINT_ERRORS": [{
                            "C_ARN": c_arn_orphan,
                            "C_ADDR": c_addr_orphan,
                            "SPAT_STS": "OUTSIDE",
                            "MATCH_TYP": "FAIL",
                            "ERR_CODE": "E02_ORPHAN",
                            "ERR_DESC": "Point outside any parcel"
                        }],
                        "ERR_LIST_OVERRIDE": orphan_err_list
                    }

        messages.addMessage("Collapsing records to one parcel per issue group...")

        error_records = []

        for target_id, rec in parcel_errors.items():
            errs = rec["POINT_ERRORS"]

            if not errs:
                continue

            codes = sorted(list({e["ERR_CODE"] for e in errs}))

            if len(codes) == 1:
                err_code = codes[0]
                err_desc = next(e["ERR_DESC"] for e in errs if e["ERR_CODE"] == err_code)
            else:
                err_code = "E00_MULTI"
                err_desc = "Multiple error types found"

            spat_values = sorted(list({e["SPAT_STS"] for e in errs if e.get("SPAT_STS")}))
            if len(spat_values) == 1:
                spat_sts = spat_values[0]
            elif len(spat_values) > 1:
                spat_sts = "MIXED"
            else:
                spat_sts = ""

            match_values = sorted(list({e["MATCH_TYP"] for e in errs if e.get("MATCH_TYP")}))
            if len(match_values) == 1:
                match_typ = match_values[0]
            elif len(match_values) > 1:
                match_typ = "MIXED"
            else:
                match_typ = ""

            if "ERR_LIST_OVERRIDE" in rec:
                err_list = rec["ERR_LIST_OVERRIDE"]
            else:
                err_list_items = []
                for e in errs:
                    c_id = e["C_ARN"] if e["C_ARN"] else "NOARN"
                    c_add = str(e["C_ADDR"]).strip() if e["C_ADDR"] else "NOADDR"
                    err_list_items.append(f"{c_id}|{c_add}|{e['ERR_CODE']}")

                err_list = truncate_text("; ".join(err_list_items), 250)

            first_err = errs[0]

            error_records.append({
                "SHAPE@": rec["SHAPE@"],
                "P_ARN": rec["P_ARN"],
                "P_ADDR": rec["P_ADDR"],
                "C_ARN": first_err.get("C_ARN", ""),
                "C_ADDR": first_err.get("C_ADDR", ""),
                "SPAT_STS": spat_sts,
                "MATCH_TYP": match_typ,
                "ERR_CODE": err_code,
                "ERR_DESC": err_desc,
                "ERR_LIST": err_list,
                "PT_COUNT": str(rec["PT_COUNT"]),
                "C_LIST": rec["C_LIST"],
                "NOTE": rec["NOTE"],
                "REVIEW_FLG": "Y"
            })

        messages.addMessage("Deduplicating final records...")
        unique_records = []
        seen = set()

        for rec in error_records:
            geom_wkt = rec["SHAPE@"].WKT if rec["SHAPE@"] else ""
            key = (
                rec["P_ARN"],
                rec["ERR_CODE"],
                rec["ERR_LIST"],
                geom_wkt
            )

            if key not in seen:
                seen.add(key)
                unique_records.append(rec)

        error_records = unique_records

        messages.addMessage(f"Found {len(error_records)} collapsed discrepancy records. Building output schema...")

        out_fields = [
            ("P_ARN", "TEXT", "Parcel ARN", 50),
            ("P_ADDR", "TEXT", "Parcel Address", 150),
            ("C_ARN", "TEXT", "Civic ARN", 50),
            ("C_ADDR", "TEXT", "Civic Address", 150),
            ("SPAT_STS", "TEXT", "Spatial Status", 20),
            ("MATCH_TYP", "TEXT", "Match Type", 20),
            ("ERR_CODE", "TEXT", "Error Code", 20),
            ("ERR_DESC", "TEXT", "Error Description", 100),
            ("ERR_LIST", "TEXT", "Error List", 250),
            ("PT_COUNT", "TEXT", "Point Count", 10),
            ("C_LIST", "TEXT", "Civic List", 250),
            ("NOTE", "TEXT", "Notes", 30),
            ("REVIEW_FLG", "TEXT", "Review Flag", 10)
        ]

        temp_fc = "memory/illusync_errors"

        arcpy.management.CreateFeatureclass(
            out_path="memory",
            out_name="illusync_errors",
            geometry_type="POLYGON",
            spatial_reference=arcpy.Describe(parcel_lyr).spatialReference
        )

        for field in out_fields:
            arcpy.management.AddField(
                temp_fc,
                field[0],
                field[1],
                field_length=field[3],
                field_alias=field[2]
            )

        messages.addMessage("Writing error records to disk...")
        insert_fields = ["SHAPE@"] + [f[0] for f in out_fields]

        with arcpy.da.InsertCursor(temp_fc, insert_fields) as cursor:
            for record in error_records:
                row = [
                    record.get("SHAPE@"),
                    record.get("P_ARN", ""),
                    record.get("P_ADDR", ""),
                    record.get("C_ARN", ""),
                    record.get("C_ADDR", ""),
                    record.get("SPAT_STS", ""),
                    record.get("MATCH_TYP", ""),
                    record.get("ERR_CODE", ""),
                    record.get("ERR_DESC", ""),
                    record.get("ERR_LIST", ""),
                    record.get("PT_COUNT", ""),
                    record.get("C_LIST", ""),
                    record.get("NOTE", ""),
                    record.get("REVIEW_FLG", "Y")
                ]
                cursor.insertRow(row)

        arcpy.management.CopyFeatures(temp_fc, out_fc)

        arcpy.management.Delete(join_out)
        if orphan_count > 0:
            arcpy.management.Delete(orphan_buff)
        arcpy.management.Delete(temp_fc)
        arcpy.management.Delete("civic_mem")

        messages.addMessage("IlluSync validation complete.")
        return
