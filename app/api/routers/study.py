import asyncio
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException

from app.api.deps import get_db, get_services
from app.api.schemas import FlashcardRequest, QuizRequest, StudySetGenerateRequest
from app.auth import AuthenticatedUser, get_current_user
from app.services.ownership import get_owned_document_metadata
from app.services.study_sets import build_study_set_record, normalize_study_set_type

router = APIRouter(tags=["study"])


@router.post("/study-sets/generate")
async def generate_study_set(
    request: StudySetGenerateRequest,
    current_user: AuthenticatedUser = Depends(get_current_user),
):
    services = get_services()
    try:
        study_type = normalize_study_set_type(request.type)
        metadata = get_owned_document_metadata(get_db(), services.vector_store, current_user.username, request.filename)
        generated = await asyncio.to_thread(
            services.study_set_generator.generate_study_set,
            request.filename,
            study_type,
            request.num_items,
            request.difficulty,
            Path(metadata["processed_path"]),
        )
        study_set = get_db().create_study_set(
            current_user.username,
            build_study_set_record(
                generated,
                study_type=study_type,
                source_filename=request.filename,
                difficulty=request.difficulty,
                model=services.study_set_generator.model_id,
            ),
        )
        return study_set
    except HTTPException:
        raise
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Document not found or not processed yet")
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Error generating study set: {str(exc)}")


@router.get("/study-sets")
async def list_study_sets(current_user: AuthenticatedUser = Depends(get_current_user)):
    return {"study_sets": get_db().list_study_sets(current_user.username)}


@router.get("/study-sets/{study_set_id}")
async def get_study_set(study_set_id: str, current_user: AuthenticatedUser = Depends(get_current_user)):
    study_set = get_db().get_study_set(current_user.username, study_set_id)
    if not study_set:
        raise HTTPException(status_code=404, detail="Study set not found")
    return study_set


@router.delete("/study-sets/{study_set_id}")
async def delete_study_set(study_set_id: str, current_user: AuthenticatedUser = Depends(get_current_user)):
    if get_db().delete_study_set(current_user.username, study_set_id):
        return {"message": "Study set deleted successfully"}
    raise HTTPException(status_code=404, detail="Study set not found")


@router.post("/quiz/generate")
async def generate_quiz(request: QuizRequest, current_user: AuthenticatedUser = Depends(get_current_user)):
    services = get_services()
    try:
        metadata = get_owned_document_metadata(get_db(), services.vector_store, current_user.username, request.filename)
        quiz = await asyncio.to_thread(
            services.quiz_generator.generate_quiz,
            request.filename,
            request.num_questions,
            request.difficulty,
            Path(metadata["processed_path"]),
        )
        return quiz
    except HTTPException:
        raise
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Document not found or not processed yet")
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Error generating quiz: {str(exc)}")


@router.post("/flashcards/generate")
async def generate_flashcards(request: FlashcardRequest, current_user: AuthenticatedUser = Depends(get_current_user)):
    services = get_services()
    try:
        metadata = get_owned_document_metadata(get_db(), services.vector_store, current_user.username, request.filename)
        flashcards = await asyncio.to_thread(
            services.flashcard_generator.generate_flashcards,
            request.filename,
            request.num_cards,
            Path(metadata["processed_path"]),
        )
        return flashcards
    except HTTPException:
        raise
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Document not found or not processed yet")
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Error generating flashcards: {str(exc)}")
