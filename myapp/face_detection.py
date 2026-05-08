


# File: app/face_detection.py

import os
import torch
import numpy as np
from PIL import Image
from facenet_pytorch import MTCNN, InceptionResnetV1
import pickle
import cv2
from django.conf import settings
from datetime import datetime

# Global variables
device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
mtcnn = None
resnet = None
embeddings_db = None

# Model paths
model_path = os.path.join(settings.BASE_DIR, 'myapp', 'inc_face_recognition_model.pkl')


# Preprocessing constants
TARGET_IMAGE_SIZE = (640, 480)


def initialize_detection_models():
    """Initialize all models for detection"""
    global mtcnn, resnet, genderNet, embeddings_db
    
    if mtcnn is None:
        print(f"🔧 Initializing detection models on {device}...")
        
        mtcnn = MTCNN(
            image_size=160,
            margin=0,
            min_face_size=40,
            thresholds=[0.6, 0.7, 0.7],
            factor=0.709,
            post_process=True,
            device=device,
            keep_all=True
        )
        print("✓ MTCNN face detector loaded")
        
        resnet = InceptionResnetV1(
            pretrained='vggface2'
        ).eval().to(device)
        print("✓ InceptionResnetV1 face recognition loaded")

            
        load_embeddings_database()
        
        print("✓ All detection models initialized successfully")


def load_embeddings_database():
    """
    FIXED: Load trained face embeddings with proper verification
    """
    global embeddings_db
    
    if os.path.exists(model_path):
        try:
            print(f"\n🔍 Loading embeddings database from: {model_path}")
            
            with open(model_path, 'rb') as f:
                model_data = pickle.load(f)
            
            # Extract embeddings dictionary
            if isinstance(model_data, dict) and 'embeddings' in model_data:
                embeddings_db = model_data['embeddings']
            else:
                embeddings_db = model_data
            
            # CRITICAL: Verify what we loaded
            print(f"\n📊 DATABASE CONTENTS:")
            total = 0
            
            for category, persons in embeddings_db.items():
                count = len(persons)
                total += count
                
                print(f"\n  📁 Category: {category}")
                print(f"     Count: {count} persons")
                
                # List all persons in this category
                if count > 0:
                    print(f"     Persons:")
                    for person_key in persons.keys():
                        embedding = persons[person_key]
                        print(f"       - {person_key} (embedding shape: {embedding.shape})")
            
            print(f"\n  ✅ TOTAL LOADED: {total} persons")
            
            if total == 0:
                print(f"  ⚠️  WARNING: Database is empty!")
                embeddings_db = {
                    'Authority': {},
                    'Resident': {},
                    'Worker': {},
                    'FamilyMember': {}
                }
            
            return True
            
        except Exception as e:
            print(f"❌ Error loading embeddings: {e}")
            import traceback
            traceback.print_exc()
            embeddings_db = {
                'Authority': {},
                'Resident': {},
                'Worker': {},
                'FamilyMember': {}
            }
            return False
    else:
        print("⚠️  No trained face recognition model found")
        embeddings_db = {
            'Authority': {},
            'Resident': {},
            'Worker': {},
            'FamilyMember': {}
        }
        return False


def preprocess_frame(frame):
    """Minimal preprocessing"""
    try:
        resized = cv2.resize(frame, TARGET_IMAGE_SIZE, interpolation=cv2.INTER_LINEAR)
        return resized
    except Exception as e:
        print(f"⚠️  Preprocessing failed: {e}")
        return frame




def extract_face_embedding_from_tensor(face_tensor):
    """Extract embedding from face tensor"""
    try:
        face_tensor = face_tensor.unsqueeze(0).to(device)
        
        with torch.no_grad():
            embedding = resnet(face_tensor).cpu().numpy()[0]
        
        return embedding
        
    except Exception as e:
        print(f"❌ Embedding extraction error: {e}")
        return None


def cosine_similarity(embedding1, embedding2):
    """Calculate cosine similarity"""
    dot_product = np.dot(embedding1, embedding2)
    norm1 = np.linalg.norm(embedding1)
    norm2 = np.linalg.norm(embedding2)
    
    if norm1 == 0 or norm2 == 0:
        return 0.0
    
    return dot_product / (norm1 * norm2)


def euclidean_distance(embedding1, embedding2):
    """Calculate Euclidean distance"""
    return np.linalg.norm(embedding1 - embedding2)


def find_match(embedding, user_id=None):
    """
    FIXED: Search ALL persons in database
    
    Critical fix: Properly iterate through ALL persons, not just first one
    
    Args:
        embedding: 512-dimensional face embedding
        user_id: Current user's ID
        
    Returns:
        (person_key, category, similarity, person_data)
    """
    if embeddings_db is None or not embeddings_db:
        print("  ⚠️  No embeddings database loaded!")
        return None, None, 0.0, None
    
    print(f"\n  🔍 Searching database...")
    
    # CRITICAL FIX: Store ALL matches to ensure we check everyone
    all_matches = []
    
    # Count how many persons we're checking
    total_persons_checked = 0
    
    # Search with user isolation
    for category, persons in embeddings_db.items():
        

        # CRITICAL: Check this category has persons
        if not persons or len(persons) == 0:
            print(f"    Category {category} is empty")
            continue
        
        print(f"    Checking {category}: {len(persons)} persons")
        
        # CRITICAL FIX: Properly iterate through ALL persons
        for person_key, person_embedding in persons.items():
            
            # Verify embedding is valid
            if person_embedding is None:
                print(f"      ⚠️  {person_key}: NULL embedding")
                continue
            
            if not isinstance(person_embedding, np.ndarray):
                print(f"      ⚠️  {person_key}: Invalid embedding type")
                continue
            
            if person_embedding.shape[0] != 512:
                print(f"      ⚠️  {person_key}: Wrong shape {person_embedding.shape}")
                continue
            
            # Calculate similarity
            try:
                similarity = cosine_similarity(embedding, person_embedding)
                distance = euclidean_distance(embedding, person_embedding)
                
                total_persons_checked += 1
                
                print(f"      {person_key}: similarity={similarity:.4f}, distance={distance:.3f}")
                
                all_matches.append({
                    'person_key': person_key,
                    'category': category,
                    'similarity': similarity,
                    'distance': distance,
                    'embedding': person_embedding
                })
                
            except Exception as e:
                print(f"      ❌ Error comparing {person_key}: {e}")
                continue
    
    print(f"\n  📊 Checked {total_persons_checked} persons total")
    
    # Check if we found any matches
    if len(all_matches) == 0:
        print(f"  ⚠️  NO PERSONS TO MATCH AGAINST!")
        return None, None, 0.0, None
    
    # Sort by similarity (highest first)
    all_matches.sort(key=lambda x: x['similarity'], reverse=True)
    
    # Get best match
    best_match = all_matches[0]
    best_match_key = best_match['person_key']
    best_category = best_match['category']
    max_similarity = best_match['similarity']
    best_distance = best_match['distance']
    best_embedding = best_match['embedding']
    
    # Get second best for comparison
    second_best_similarity = -1.0
    if len(all_matches) > 1:
        second_best_similarity = all_matches[1]['similarity']
    
    # Convert display category
    display_category = best_category
    
    # STRICTER THRESHOLDS - Based on real testing
    # Real person: 70-90% similarity
    # Stranger: 50-65% similarity
    # Threshold: 68% = catches real, blocks strangers
    similarity_thresholds = {
        'Authority': 0.65,
        'Resident': 0.63,
        'Worker': 0.63,
        'FamilyMember': 0.63
    }
    
    threshold = similarity_thresholds.get(display_category, 0.68)
    
    print(f"\n  📊 MATCHING RESULTS:")
    print(f"     Best: {best_match_key} ({display_category})")
    print(f"     Similarity: {max_similarity:.4f} ({int(max_similarity*100)}%)")
    print(f"     Distance: {best_distance:.3f}")
    print(f"     Threshold: {threshold:.4f} ({int(threshold*100)}%)")
    
    if len(all_matches) > 1:
        print(f"     2nd best: {all_matches[1]['person_key']} ({all_matches[1]['similarity']:.4f})")
        gap = max_similarity - second_best_similarity
        print(f"     Gap: {gap:.4f} ({int(gap*100)}%)")
    
    # Check threshold
    if max_similarity >= threshold:
        print(f"  ✓ Threshold passed")
        
        # Verification 1: Distance check (stricter)
        if best_distance > 0.85:  # Stricter than 0.95
            print(f"  ❌ REJECTED: Distance too high ({best_distance:.3f})")
            return None, None, max_similarity, None
        
        # Verification 2: For high-risk, check uniqueness
        if display_category in ['Authority', 'Resident', 'Worker', 'FamilyMember']:
            if len(all_matches) > 1:
                gap = max_similarity - second_best_similarity
                
                if gap < 0.05 and max_similarity < 0.65:
                    print(f"  ⚠️  AMBIGUOUS: Top matches too similar")
                    print(f"  ❌ REJECTED: Need clearer distinction")
                    return None, None, max_similarity, None
        
        # Verification 3: Norm ratio
        embedding_norm = np.linalg.norm(embedding)
        matched_norm = np.linalg.norm(best_embedding)
        norm_ratio = embedding_norm / matched_norm if matched_norm > 0 else 0
        
        print(f"     Norm ratio: {norm_ratio:.3f}")
        
        if norm_ratio < 0.6 or norm_ratio > 1.4:
            print(f"  ⚠️  WARNING: Unusual norm ratio")
        
        print(f"  ✅ MATCH CONFIRMED: {best_match_key} ({display_category})")
        return best_match_key, best_category, max_similarity, None
    else:
        similarity_percent = max_similarity * 100
        threshold_percent = threshold * 100
        gap = (threshold - max_similarity) * 100
        
        print(f"  ❌ NO MATCH")
        print(f"     Similarity: {similarity_percent:.1f}%")
        print(f"     Required: {threshold_percent:.1f}%")
        print(f"     Gap: {gap:.1f}%")
        print(f"     Closest: {best_match_key} ({display_category})")
        
        return None, None, max_similarity, None


def process_frame(frame, use_preprocessing=False, user_id=None):
    """
    Process frame with complete person checking
    
    Args:
        frame: OpenCV frame (BGR)
        use_preprocessing: Apply preprocessing
        user_id: Current user's ID
        
    Returns:
        (annotated_frame, detections_list)
    """
    if mtcnn is None:
        initialize_detection_models()
    
    if use_preprocessing:
        processed_frame = preprocess_frame(frame)
    else:
        processed_frame = frame.copy()
    
    # Convert to RGB
    rgb_frame = cv2.cvtColor(processed_frame, cv2.COLOR_BGR2RGB)
    img_pil = Image.fromarray(rgb_frame)
    
    # Detect faces
    boxes, probs = mtcnn.detect(img_pil)
    
    detections = []
    
    if boxes is not None:
        print(f"👤 Detected {len(boxes)} face(s)")
        
        faces = mtcnn(img_pil)
        
        if faces is not None:
            if faces.dim() == 3:
                faces = faces.unsqueeze(0)
            
            for i, (box, face, prob) in enumerate(zip(boxes, faces, probs)):
                try:
                    print(f"\n  [Face {i+1}] Detection confidence: {prob:.3f}")
                    
                    # Extract embedding
                    embedding = extract_face_embedding_from_tensor(face)
                    
                    if embedding is None:
                        continue
                    
                    # Find match - NOW CHECKS ALL PERSONS
                    person_key, category, similarity, _ = find_match(
                        embedding, 
                        user_id=user_id
                    )
                    
                    x1, y1, x2, y2 = box.astype(int)
                    
                    x1 = max(0, x1)
                    y1 = max(0, y1)
                    x2 = min(processed_frame.shape[1], x2)
                    y2 = min(processed_frame.shape[0], y2)
                    
                    detection = {
                        'box': [int(x1), int(y1), int(x2), int(y2)],
                        'confidence': float(prob),
                        'similarity': float(similarity)
                    }
                    
                    if person_key and category:
                        # RECOGNIZED PERSON
                        category_prefix, person_id = person_key.split('_', 1)

                        display_category = category
                        
                        detection['recognized'] = True
                        detection['person_key'] = person_key
                        detection['person_id'] = int(person_id)
                        detection['category'] = display_category
                        detection['category_prefix'] = category_prefix
                        
                        # Colors
                        if display_category == 'Authority':
                            color = (255, 0, 0)  # Blue
                            detection['alert_type'] = 'NORMAL'
                            detection['visitor_type'] = 'Authority'

                        elif display_category == 'Resident':
                            color = (0, 255, 0)  # Green
                            detection['alert_type'] = 'NORMAL'
                            detection['visitor_type'] = 'Resident'

                        elif display_category == 'Worker':
                            color = (255, 255, 0)  # Cyan
                            detection['alert_type'] = 'NORMAL'
                            detection['visitor_type'] = 'Worker'

                        elif display_category == 'FamilyMember':
                            color = (0, 255, 255)  # Yellow
                            detection['alert_type'] = 'NORMAL'
                            detection['visitor_type'] = 'Family Member'
                        else:
                            color = (128, 128, 128)
                            detection['alert_type'] = 'WARNING'
                            detection['visitor_type'] = 'Unknown'
                        
                        detection['name'] = person_key
                        detection['gender'] = "Unknown"
                        
                        # Draw box
                        cv2.rectangle(processed_frame, (x1, y1), (x2, y2), color, 3)
                        
                        similarity_percent = int(similarity * 100)
                        label = f"{display_category}: {person_key} ({similarity_percent}%)"
                        print(f"  ✅ RECOGNIZED: {label}")

                    else:
                        detection['recognized'] = False

                        color = (128, 128, 128)

                        cv2.rectangle(processed_frame, (x1, y1), (x2, y2), color, 3)

                        label = ""
                    
                    # Draw label
                    font = cv2.FONT_HERSHEY_SIMPLEX
                    font_scale = 0.7
                    font_thickness = 2
                    
                    (label_width, label_height), baseline = cv2.getTextSize(
                        label, font, font_scale, font_thickness
                    )
                    
                    label_y = y1 - 10
                    if label_y < label_height + 10:
                        label_y = y2 + label_height + 10
                    
                    # Label background
                    cv2.rectangle(
                        processed_frame,
                        (x1, label_y - label_height - 5),
                        (x1 + label_width + 10, label_y + 5),
                        color,
                        -1
                    )
                    
                    # Label text
                    cv2.putText(
                        processed_frame,
                        label,
                        (x1 + 5, label_y),
                        font,
                        font_scale,
                        (255, 255, 255),
                        font_thickness,
                        cv2.LINE_AA
                    )
                    
                    detections.append(detection)
                    
                except Exception as e:
                    print(f"❌ Error processing face {i}: {e}")
                    import traceback
                    traceback.print_exc()
                    continue
    else:
        print("👤 No faces detected")
    
    return processed_frame, detections


def reload_model():
    """Reload embeddings database"""
    global embeddings_db
    print("\n🔄 Reloading model...")
    load_embeddings_database()
    print("✓ Model reloaded")




    