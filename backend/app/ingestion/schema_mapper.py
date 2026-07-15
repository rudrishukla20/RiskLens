"""
Schema mapper — persists confirmed or auto-inferred column mappings.

Writes ``SchemaMapping`` and ``DatasetColumn`` rows to the database
using the repository layer.
"""

import logging
import uuid
from datetime import datetime, timezone
from typing import Dict, List, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.ingestion.schema_inferer import InferredColumn
from app.models.dataset_column import DatasetColumn
from app.models.schema_mapping import SchemaMapping
from app.repositories.dataset_repository import DatasetRepository
from app.repositories.schema_mapping_repository import SchemaMappingRepository

logger = logging.getLogger(__name__)


async def persist_inferred_columns(
    db: AsyncSession,
    dataset_id: uuid.UUID,
    version_id: uuid.UUID,
    inferred_columns: List[InferredColumn],
) -> List[DatasetColumn]:
    """
    Persist inferred column metadata (before mapping confirmation).

    Creates one ``DatasetColumn`` row per inferred column so the UI
    can display detected columns with their types and sample values.

    Returns
    -------
    list[DatasetColumn]
        The created column records.
    """
    dataset_repo = DatasetRepository(db)
    created: List[DatasetColumn] = []

    for col in inferred_columns:
        dc = DatasetColumn(
            id=uuid.uuid4(),
            dataset_id=dataset_id,
            version_id=version_id,
            original_column_name=col.original_name,
            canonical_column_name=col.candidate_canonical_field,
            inferred_data_type=col.inferred_dtype,
            is_required=False,
            is_mapped=col.candidate_canonical_field is not None,
            sample_values_json=col.sample_values,
        )
        db.add(dc)
        created.append(dc)

    await db.flush()
    logger.info(
        "Persisted %d inferred DatasetColumn rows for dataset %s",
        len(created),
        dataset_id,
    )
    return created


async def persist_confirmed_mappings(
    db: AsyncSession,
    dataset_id: uuid.UUID,
    version_id: uuid.UUID,
    mappings: List[Dict[str, str]],
    confirmed_by: Optional[uuid.UUID] = None,
) -> List[SchemaMapping]:
    """
    Persist user-confirmed (or auto-accepted) canonical field mappings.

    Parameters
    ----------
    mappings : list[dict]
        Each dict must contain ``original_column_name`` and ``canonical_field``.
        Optional: ``confidence_score``, ``mapping_source``.

    Returns
    -------
    list[SchemaMapping]
    """
    mapping_repo = SchemaMappingRepository(db)

    # Clear prior mappings for this dataset+version to avoid duplicates
    await mapping_repo.delete_by_dataset(dataset_id, version_id)

    created: List[SchemaMapping] = []
    now = datetime.now(timezone.utc)

    for m in mappings:
        sm = SchemaMapping(
            id=uuid.uuid4(),
            dataset_id=dataset_id,
            version_id=version_id,
            original_column_name=m["original_column_name"],
            canonical_field=m["canonical_field"],
            confidence_score=float(m.get("confidence_score", 1.0)),
            mapping_source=m.get("mapping_source", "MANUAL"),
            confirmed_by=confirmed_by,
            confirmed_at=now if confirmed_by else None,
        )
        db.add(sm)
        created.append(sm)

    # Also update DatasetColumn rows to reflect mapping state
    dataset_repo = DatasetRepository(db)
    existing_columns = await dataset_repo.get_columns(dataset_id, version_id)

    mapping_lookup: Dict[str, str] = {m["original_column_name"]: m["canonical_field"] for m in mappings}
    for dc in existing_columns:
        if dc.original_column_name in mapping_lookup:
            dc.canonical_column_name = mapping_lookup[dc.original_column_name]
            dc.is_mapped = True
            dc.mapped_data_type = dc.inferred_data_type
            db.add(dc)

    await db.flush()
    logger.info(
        "Persisted %d confirmed SchemaMapping rows for dataset %s",
        len(created),
        dataset_id,
    )
    return created
