# basicly just supporting code, basic file parsing and data processing to get the dataset ready for the LSTM mostly ai generated
import os
import sys
import re
import xml.etree.ElementTree as ET
import random
from recognizer import DollarRecognizer, Point


def parse_xml_gesture(file_path):
    """Parses a single Wobbrock XML log file into a clean label and Point array."""
    try:
        tree = ET.parse(file_path)
        root = tree.getroot()
        
        # Extract the raw name (e.g., 'arrow06') and strip digits to get the class label ('arrow')
        raw_name = root.attrib.get('Name', 'unknown')
        label = re.sub(r'\d+', '', raw_name).lower()
        
        points = []
        for point_tag in root.findall('Point'):
            x = float(point_tag.attrib['X'])
            y = float(point_tag.attrib['Y'])
            points.append(Point(x, y))
            
        return label, points
    except Exception as e:
        print(f"Error parsing {file_path}: {e}")
        return None, None

def load_and_split_dataset(dataset_dir, test_samples_per_class=10):
    """
    Crawls the XML logs directory, processes data through the $1 normalize pipeline,
    and returns a clean, stratified Train/Test split.
    """
    rec = DollarRecognizer(load_defaults=False)
    raw_data_by_class = {}
    
    # 1. Gather all data by its clean gesture class name
    for root_dir, _, files in os.walk(dataset_dir):
        for file in files:
            if file.endswith('.xml'):
                full_path = os.path.join(root_dir, file)
                label, points = parse_xml_gesture(full_path)
                
                if label and len(points) >= 2:
                    if label not in raw_data_by_class:
                        raw_data_by_class[label] = []
                    raw_data_by_class[label].append(points)
                    
    train_set = []
    test_set = []
    
    # 2. Process, Normalize, and Split systematically
    for label, samples in raw_data_by_class.items():
        # Shuffle to ensure random sample extraction
        random.shuffle(samples)
        
        normalized_samples = []
        for pts in samples:
            # We pass points through the $1 pipeline steps so the LSTM
            # receives perfectly uniform shape matrices (64 points, scaled, translated)
            norm_pts = rec.normalize(pts)
            normalized_samples.append(norm_pts)
            
        # Stratified Split
        if len(normalized_samples) >= test_samples_per_class:
            test_set.extend([(label, s) for s in normalized_samples[:test_samples_per_class]])
            train_set.extend([(label, s) for s in normalized_samples[test_samples_per_class:]])
        else:
            print(f"Warning: Class '{label}' only has {len(normalized_samples)} samples!")
            train_set.extend([(label, s) for s in normalized_samples])
            
    return train_set, test_set

# ----------------------------------------------------------------
# Execution Example
# ----------------------------------------------------------------
if __name__ == "__main__":
    # Point this to your unzipped XML log folder
    DATA_DIRECTORY = "./datasets/xml_logs" 
    
    train_data, test_data = load_and_split_dataset(DATA_DIRECTORY, test_samples_per_class=10)
    
    print(f"Successfully processed dataset!")
    print(f"Total Training Samples: {len(train_data)}")
    print(f"Total Test Samples:     {len(test_data)}")
    
    # Preview format
    first_label, first_points = train_data[0]
    print(f"\nFirst training sample label: '{first_label}'")
    print(f"Points shape array: {len(first_points)} points ready for Tensor conversion.")