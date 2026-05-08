
# ==================== COMPLETE FIXED face_training.py ====================

import os
import torch
import numpy as np
from PIL import Image
import pickle
from django.conf import settings
from facenet_pytorch import MTCNN, InceptionResnetV1
import cv2
from PIL import ImageOps

# Global variables
device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
mtcnn = None
resnet = None

model_path = os.path.join(settings.BASE_DIR, 'myapp', 'inc_face_recognition_model.pkl')

# Constants
TARGET_IMAGE_SIZE = (640, 480)
MIN_IMAGE_SIZE = (160, 160)
JPEG_QUALITY = 95


def initialize_models():
    """Initialize MTCNN and InceptionResnetV1 models"""
    global mtcnn, resnet

    if mtcnn is None:
        print(f"🔧 Initializing training models on {device}...")

        # SAME settings as detection
        mtcnn = MTCNN(
            image_size=160,
            margin=0,
            min_face_size=40,
            thresholds=[0.6, 0.7, 0.7],
            factor=0.709,
            post_process=True,
            device=device
        )

        resnet = InceptionResnetV1(
            pretrained='vggface2'
        ).eval().to(device)

        print("✓ Models initialized successfully")


def fix_mobile_image_orientation(image):
    """Fix image orientation from mobile cameras"""
    try:
        image = ImageOps.exif_transpose(image)
        return image
    except:
        return image


def extract_face_embedding(image_path, use_preprocessing=True):
    """Extract face embedding - MINIMAL preprocessing"""
    try:
        print(f"  📸 Processing: {os.path.basename(image_path)}")

        # Load and fix orientation
        img = Image.open(image_path)
        img = fix_mobile_image_orientation(img)

        if img.mode != 'RGB':
            if img.mode == 'RGBA':
                background = Image.new('RGB', img.size, (255, 255, 255))
                background.paste(img, mask=img.split()[3])
                img = background
            else:
                img = img.convert('RGB')

        # Just resize if too large
        max_size = 1024
        if img.size[0] > max_size or img.size[1] > max_size:
            img.thumbnail((max_size, max_size), Image.Resampling.LANCZOS)

        # Try detection
        face = mtcnn(img)

        if face is not None:
            print(f"  ✅ Face detected")

            face = face.unsqueeze(0).to(device)
            with torch.no_grad():
                embedding = resnet(face).cpu().numpy()[0]

            print(f"  ✅ Embedding extracted (shape: {embedding.shape})")
            return embedding

        # Try relaxed settings
        print(f"  🔄 Trying relaxed detection...")
        mtcnn_relaxed = MTCNN(
            image_size=160,
            margin=0,
            min_face_size=20,
            thresholds=[0.5, 0.6, 0.6],
            factor=0.709,
            post_process=True,
            device=device
        )

        face = mtcnn_relaxed(img)

        if face is not None:
            print(f"  ✅ Face detected with relaxed settings")
            face = face.unsqueeze(0).to(device)
            with torch.no_grad():
                embedding = resnet(face).cpu().numpy()[0]
            return embedding

        print(f"  ❌ No face detected")
        return None

    except Exception as e:
        print(f"  ❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return None


def load_existing_model():
    """Load existing model or create new"""
    model_dir = os.path.dirname(model_path)
    if not os.path.exists(model_dir):
        os.makedirs(model_dir, exist_ok=True)

    if os.path.exists(model_path):
        try:
            with open(model_path, 'rb') as f:
                model_data = pickle.load(f)

            if isinstance(model_data, dict) and 'embeddings' in model_data:
                embeddings_db = model_data['embeddings']
            else:
                embeddings_db = model_data

            print(f"✓ Loaded existing model")

            for category, persons in embeddings_db.items():
                print(f"  {category}: {len(persons)} persons")

            return embeddings_db
        except Exception as e:
            print(f"⚠️  Error loading model: {e}")
            return {
                'Authority': {},
                'Resident': {},
                'Worker': {},
                'FamilyMember': {}
            }
    else:
        print("📝 No existing model. Creating new.")
        return {
            'Authority': {},
            'Resident': {},
            'Worker': {},
            'FamilyMember': {}
        }

def train_face_recognition(person_id, category, photo_paths, user_id=None):
    """
    Train face recognition
    FIXED: Now correctly saves Criminal and Missing to global categories
    
    Args:
        person_id: ID of the person
        category: 'criminal', 'familiar', or 'missing'
        photo_paths: List of image paths
        user_id: User ID (only for familiar persons)
    """
    try:
        print("\n" + "="*70)
        print(f"🎓 TRAINING FACE RECOGNITION")
        print("="*70)

        initialize_models()
        embeddings_db = load_existing_model()

        # Map category names
        category_map = {
            'authority': 'Authority',
            'resident': 'Resident',
            'worker': 'Worker',
            'familymember': 'FamilyMember'
        }
        category_name = category_map.get(category.lower(), category)

        # ============ DETERMINE STORAGE CATEGORY ============

        category_key = category_name
        print(f"📌 Category: {category_key} (GLOBAL)")

        # Create category if doesn't exist
        if category_key not in embeddings_db:
            embeddings_db[category_key] = {}
            print(f"✓ Created new category: {category_key}")

        person_key = f"{category.lower()}_{person_id}"

        print(f"📌 Person Key: {person_key}")
        print(f"📂 Will save to: embeddings_db['{category_key}']['{person_key}']")
        print(f"📸 Processing {len(photo_paths)} images")
        print("-"*70)

        # ============ EXTRACT EMBEDDINGS ============
        embeddings_list = []

        for i, photo_path in enumerate(photo_paths, 1):
            print(f"\n[Image {i}/{len(photo_paths)}]")
            print(f"File: {os.path.basename(photo_path)}")

            if not os.path.exists(photo_path):
                print(f"❌ File not found")
                continue

            embedding = extract_face_embedding(photo_path)

            if embedding is not None:
                embeddings_list.append(embedding)
                print(f"✅ Success")
            else:
                print(f"❌ Failed")

        print("\n" + "-"*70)
        print(f"📊 RESULTS: {len(embeddings_list)}/{len(photo_paths)} successful")

        if len(embeddings_list) == 0:
            print("❌ TRAINING FAILED: No faces detected")
            print("="*70 + "\n")
            return False, "❌ No valid faces detected"

        # ============ COMPUTE AVERAGE EMBEDDING ============
        print(f"\n🧮 Computing average embedding...")
        avg_embedding = np.mean(embeddings_list, axis=0)

        if avg_embedding.shape[0] != 512:
            print(f"❌ Invalid embedding shape: {avg_embedding.shape}")
            return False, f"❌ Invalid embedding dimension"

        print(f"✓ Computed average embedding")
        print(f"  Shape: {avg_embedding.shape}")
        print(f"  Range: [{avg_embedding.min():.3f}, {avg_embedding.max():.3f}]")

        # ============ SAVE TO DATABASE ============
        print(f"\n💾 Saving to database...")

        # Add to embeddings database
        embeddings_db[category_key][person_key] = avg_embedding

        print(f"✓ Added to memory:")
        print(f"  embeddings_db['{category_key}']['{person_key}'] = embedding")

        # Prepare model data
        model_data = {
            'embeddings': embeddings_db,
            'train_ratio': 0.7,
            'val_ratio': 0.15,
            'test_ratio': 0.15,
            'last_updated': str(np.datetime64('now')),
            'preprocessing_enabled': False,
            'target_size': TARGET_IMAGE_SIZE,
            'user_isolation': True
        }

        # Save to file
        print(f"\n💾 Writing to file: {model_path}")
        with open(model_path, 'wb') as f:
            pickle.dump(model_data, f)

        file_size = os.path.getsize(model_path) / 1024
        print(f"✓ File saved ({file_size:.2f} KB)")

        # ============ VERIFY SAVE ============
        print(f"\n🔍 Verifying save...")
        try:
            with open(model_path, 'rb') as f:
                verify_data = pickle.load(f)
                verify_db = verify_data['embeddings']

            if category_key in verify_db:
                if person_key in verify_db[category_key]:
                    print(f"✅ VERIFICATION PASSED")
                    print(f"   Found: {person_key} in {category_key}")
                    print(f"   Total persons in {category_key}: {len(verify_db[category_key])}")
                else:
                    print(f"❌ VERIFICATION FAILED: {person_key} NOT in {category_key}")
                    print(f"   Keys in {category_key}: {list(verify_db[category_key].keys())}")
            else:
                print(f"❌ VERIFICATION FAILED: Category {category_key} doesn't exist")
                print(f"   Available categories: {list(verify_db.keys())}")

        except Exception as verify_error:
            print(f"❌ Verification error: {verify_error}")

        # ============ DISPLAY STATS ============
        print(f"\n📈 COMPLETE DATABASE:")

        total = 0
        for cat, persons in embeddings_db.items():
            count = len(persons)
            total += count
            print(f"  {cat}: {count} persons")

        print(f"  TOTAL: {total} persons")

        print("\n" + "="*70)
        print("✅ TRAINING COMPLETED SUCCESSFULLY")
        print("="*70 + "\n")

        return True, f"✅ Training successful! Used {len(embeddings_list)}/{len(photo_paths)} images."

    except Exception as e:
        import traceback
        print("\n" + "="*70)
        print("❌ TRAINING ERROR")
        print("="*70)
        traceback.print_exc()
        print("="*70 + "\n")
        return False, f"❌ Training error: {str(e)}"


def delete_person_from_model(person_id, category, user_id=None):
    """Remove person from model"""
    try:
        print(f"\n🗑️  Removing person from model...")

        embeddings_db = load_existing_model()

        category_map = {
            'authority': 'Authority',
            'resident': 'Resident',
            'worker': 'Worker',
            'familymember': 'FamilyMember'
        }
        category_name = category_map.get(category.lower(), category)
        category_key = category_name

        person_key = f"{category.lower()}_{person_id}"

        print(f"   Looking for: {category_key}['{person_key}']")

        if category_key in embeddings_db and person_key in embeddings_db[category_key]:
            del embeddings_db[category_key][person_key]

            model_data = {
                'embeddings': embeddings_db,
                'train_ratio': 0.7,
                'val_ratio': 0.15,
                'test_ratio': 0.15,
                'last_updated': str(np.datetime64('now')),
                'user_isolation': True
            }

            with open(model_path, 'wb') as f:
                pickle.dump(model_data, f)

            print(f"✓ Removed {person_key} from {category_key}")

            total = sum(len(persons) for persons in embeddings_db.values())
            print(f"✓ Database now has {total} total persons")

            return True, f"✅ Person removed"
        else:
            print(f"⚠️  Not found")
            print(f"   Available categories: {list(embeddings_db.keys())}")
            if category_key in embeddings_db:
                print(f"   Persons in {category_key}: {list(embeddings_db[category_key].keys())}")
            return False, f"⚠️  Person not found"

    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return False, f"❌ Error: {str(e)}"


def update_person_images(person_id, category, new_photo_paths, user_id=None):
    """Update person with new images"""
    try:
        print(f"\n🔄 Updating person...")

        initialize_models()
        embeddings_db = load_existing_model()

        category_map = {
            'authority': 'Authority',
            'resident': 'Resident',
            'worker': 'Worker',
            'familymember': 'FamilyMember'
        }
        category_name = category_map.get(category.lower(), category)
        category_key = category_name

        person_key = f"{category.lower()}_{person_id}"

        if category_key not in embeddings_db or person_key not in embeddings_db[category_key]:
            return False, "❌ Person not found"

        old_embedding = embeddings_db[category_key][person_key]

        new_embeddings = []
        for photo_path in new_photo_paths:
            embedding = extract_face_embedding(photo_path)
            if embedding is not None:
                new_embeddings.append(embedding)

        if len(new_embeddings) == 0:
            return False, "❌ No valid faces in new images"

        # Weighted average
        old_weight = 5
        new_weight = len(new_embeddings)

        combined_embedding = (old_embedding * old_weight +
                            np.sum(new_embeddings, axis=0)) / (old_weight + new_weight)

        embeddings_db[category_key][person_key] = combined_embedding

        model_data = {
            'embeddings': embeddings_db,
            'train_ratio': 0.7,
            'val_ratio': 0.15,
            'test_ratio': 0.15,
            'last_updated': str(np.datetime64('now')),
            'user_isolation': True
        }

        with open(model_path, 'wb') as f:
            pickle.dump(model_data, f)

        return True, f"✅ Updated with {len(new_embeddings)} new images"

    except Exception as e:
        return False, f"❌ Error: {str(e)}"


def get_model_summary():
    """Get model summary"""
    try:
        embeddings_db = load_existing_model()

        summary = {
            'total_persons': sum(len(persons) for persons in embeddings_db.values()),
            'categories': {},
            'model_path': model_path,
            'model_exists': os.path.exists(model_path)
        }

        for category, persons in embeddings_db.items():
            summary['categories'][category] = {
                'count': len(persons),
                'persons': list(persons.keys())
            }

        return summary
    except Exception as e:
        return {'error': str(e)}


def diagnose_images(photo_paths):
    """Diagnose images before training"""
    print("\n" + "="*70)
    print("🔍 IMAGE DIAGNOSTICS")
    print("="*70)

    initialize_models()

    diagnostics = {
        'total': len(photo_paths),
        'valid': 0,
        'invalid': 0,
        'details': []
    }

    for i, path in enumerate(photo_paths, 1):
        print(f"\n[Image {i}/{len(photo_paths)}]")
        print(f"File: {os.path.basename(path)}")

        result = {
            'index': i,
            'filename': os.path.basename(path),
            'path': path,
            'valid': False,
            'issues': []
        }

        try:
            if not os.path.exists(path):
                result['issues'].append("File not found")
                diagnostics['invalid'] += 1
                diagnostics['details'].append(result)
                continue

            img = Image.open(path).convert('RGB')
            face = mtcnn(img)

            if face is not None:
                result['valid'] = True
                diagnostics['valid'] += 1
                print("  ✅ Face detected")
            else:
                result['issues'].append("No face detected")
                diagnostics['invalid'] += 1
                print("  ❌ No face detected")

        except Exception as e:
            result['issues'].append(f"Error: {str(e)}")
            diagnostics['invalid'] += 1

        diagnostics['details'].append(result)

    print("\n" + "="*70)
    print(f"Valid: {diagnostics['valid']}/{diagnostics['total']}")
    print("="*70 + "\n")

    return diagnostics['valid'], diagnostics