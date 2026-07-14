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
                r'\bne\b': 'northeast', r'\bnw\b': 'northwest', r'\bse\b': 'southeast', r'\bsw\b': 'southwest'
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

        messages.addMessage("Performing spatial join (Parcel target)...")
        join_out = "memory/parcel_join"
        
        field_mappings = arcpy.FieldMappings()
        
        p_arn_map = arcpy.FieldMap()
        p_arn_map.addInputField(parcel_lyr, p_arn_fld)
        p_arn_map_out = p_arn_map.outputField
        p_arn_map_out.name = "P_ARN_JOIN"
        p_arn_map.outputField = p_arn_map_out
        field_mappings.addFieldMap(p_arn_map)

        p_addr_map = arcpy.FieldMap()
        p_addr_map.addInputField(parcel_lyr, p_addr_fld)
        p_addr_map_out = p_addr_map.outputField
        p_addr_map_out.name = "P_ADDR_JOIN"
        p_addr_map.outputField = p_addr_map_out
        field_mappings.addFieldMap(p_addr_map)

        c_arn_map = arcpy.FieldMap()
        c_arn_map.addInputField(civic_lyr, c_arn_fld)
        c_arn_map_out = c_arn_map.outputField
        c_arn_map_out.name = "C_ARN_JOIN"
        c_arn_map.outputField = c_arn_map_out
        field_mappings.addFieldMap(c_arn_map)

        c_addr_map = arcpy.FieldMap()
        c_addr_map.addInputField(civic_lyr, c_addr_fld)
        c_addr_map_out = c_addr_map.outputField
        c_addr_map_out.name = "C_ADDR_JOIN"
        c_addr_map.outputField = c_addr_map_out
        field_mappings.addFieldMap(c_addr_map)

        arcpy.analysis.SpatialJoin(
            parcel_lyr, 
            civic_lyr, 
            join_out, 
            "JOIN_ONE_TO_MANY", 
            "KEEP_ALL",
            field_mappings
        )

        error_records = []
        messages.addMessage("Evaluating parcel and civic attributes...")
        
        fields = ["SHAPE@", "P_ARN_JOIN", "P_ADDR_JOIN", "C_ARN_JOIN", "C_ADDR_JOIN", "Join_Count"]
        
        with arcpy.da.SearchCursor(join_out, fields) as cursor:
            for row in cursor:
                poly_geom = row[0]
                
                p_arn = str(row[1]).strip() if row[1] is not None else ""
                p_addr_raw = row[2] if row[2] is not None else ""
                p_addr = normalize_text(p_addr_raw)
                
                c_arn = str(row[3]).strip() if row[3] is not None else ""
                c_addr_raw = row[4] if row[4] is not None else ""
                c_addr = normalize_text(c_addr_raw)
                
                join_count = row[5] if row[5] is not None else 0
                
                is_specific_civic = is_civic_address(p_addr)
                
                err_code = ""
                err_desc = ""
                match_typ = ""
                spat_sts = "INSIDE"
                
                if join_count == 0:
                    if is_specific_civic: 
                        err_code = "E01_MISS_PT"
                        err_desc = "Parcel has specific address but no civic point"
                        spat_sts = "MISSING"
                        match_typ = "FAIL"
                else:
                    if not c_arn and not c_addr:
                        continue
                    
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
                    elif not is_specific_civic:
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
                    error_records.append({
                        "SHAPE@": poly_geom,
                        "P_ARN": p_arn,
                        "P_ADDR": p_addr_raw,
                        "C_ARN": c_arn,
                        "C_ADDR": c_addr_raw,
                        "SPAT_STS": spat_sts,
                        "MATCH_TYP": match_typ,
                        "ERR_CODE": err_code,
                        "ERR_DESC": err_desc
                    })

        messages.addMessage("Checking for orphaned civic points...")
        arcpy.management.MakeFeatureLayer(civic_lyr, "civic_mem")
        arcpy.management.SelectLayerByLocation("civic_mem", "INTERSECT", parcel_lyr, "", "NEW_SELECTION", "INVERT")
        
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
                    error_records.append({
                        "SHAPE@": row[0],
                        "P_ARN": "",
                        "P_ADDR": "",
                        "C_ARN": str(row[1]).strip() if row[1] is not None else "",
                        "C_ADDR": row[2] if row[2] is not None else "",
                        "SPAT_STS": "OUTSIDE",
                        "MATCH_TYP": "FAIL",
                        "ERR_CODE": "E02_ORPHAN",
                        "ERR_DESC": "Point outside any parcel"
                    })

        messages.addMessage("Deduplicating records...")
        unique_records = []
        seen = set()
        for rec in error_records:
            geom_wkt = rec["SHAPE@"].WKT if rec["SHAPE@"] else ""
            key = (rec["P_ARN"], rec["C_ARN"], rec["P_ADDR"], rec["C_ADDR"], rec["ERR_CODE"], geom_wkt)
            if key not in seen:
                seen.add(key)
                unique_records.append(rec)
        error_records = unique_records

        messages.addMessage(f"Found {len(error_records)} discrepancies. Building output schema...")

        out_fields = [
            ("P_ARN", "TEXT", "Parcel ARN", 50),
            ("P_ADDR", "TEXT", "Parcel Address", 150),
            ("C_ARN", "TEXT", "Civic ARN", 50),
            ("C_ADDR", "TEXT", "Civic Address", 150),
            ("SPAT_STS", "TEXT", "Spatial Status", 20),
            ("MATCH_TYP", "TEXT", "Match Type", 20),
            ("ERR_CODE", "TEXT", "Error Code", 20),
            ("ERR_DESC", "TEXT", "Error Description", 100),
            ("REVIEW_FLG", "TEXT", "Review Flag", 10)
        ]

        temp_fc = "memory/illusync_errors"
        
        arcpy.management.CreateFeatureclass(
            out_path="memory", 
            out_name="illusync_errors", 
            geometry_type="POLYGON", 
            spatial_reference=parcel_lyr
        )
        
        for field in out_fields:
            arcpy.management.AddField(temp_fc, field[0], field[1], field_length=field[3], field_alias=field[2])

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
                    "Y"
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
