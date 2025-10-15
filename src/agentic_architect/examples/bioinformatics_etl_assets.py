"""Static assets used to generate the bioinformatics ETL CLI example project."""

from __future__ import annotations

BIOINFORMATICS_ETL_FILES: dict[str, str] = {
    "README.md": """# Bioinformatics ETL CLI\n\nThis project provides a local-first command line interface for loading genomic study TSV files into a dimensional model backed by SQL Server or SQLite.\n\n## Features\n- Study discovery with directory scanning\n- Metadata normalization and expression filtering via Polars\n- Batch loading using SQLAlchemy and pyodbc\n- Resume and rollback support backed by checkpoint metadata\n- Structured logging and metrics emission\n\n## Getting started\n```bash\nuv sync\nuv run etl run --config ./config/config.example.yaml\n```\n\n## CLI commands\n- `etl run --config ./config.yaml`\n- `etl resume --run-id <RUN_ID>`\n- `etl rollback --run-id <RUN_ID>`\n- `etl validate --input-dir <PATH>`\n- `etl report --run-id <RUN_ID>`\n""",
    "src/etl/discovery.py": """'''Module responsible for discovering study directories and required input files.'''
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Sequence

REQUIRED_TSVS = {
    'metadata': 'metadata.tsv',
    'expression': 'expression.tsv',
}


@dataclass(frozen=True)
class StudyInput:
    '''Represents a discovered study and its associated files.'''

    study_id: str
    root: Path
    files: Dict[str, Path]


class StudyDiscovery:
    '''Scan a root directory to discover studies that contain required TSV inputs.'''

    def __init__(self, required_files: Dict[str, str] | None = None) -> None:
        self._required_files = required_files or REQUIRED_TSVS

    def discover(self, root: Path) -> List[StudyInput]:
        '''Return all studies that contain the required TSV files.'''

        studies: List[StudyInput] = []
        for path in self._iter_study_dirs(root):
            files = self._collect_required_files(path)
            if files:
                studies.append(StudyInput(study_id=path.name, root=path, files=files))
        return studies

    def _iter_study_dirs(self, root: Path) -> Iterable[Path]:
        for path in root.iterdir():
            if path.is_dir():
                yield path

    def _collect_required_files(self, study_dir: Path) -> Dict[str, Path]:
        resolved: Dict[str, Path] = {}
        for key, filename in self._required_files.items():
            candidate = study_dir / filename
            if candidate.exists():
                resolved[key] = candidate
            else:
                return {}
        return resolved

    def validate(self, study: StudyInput, required_columns: Dict[str, Sequence[str]]) -> List[str]:
        '''Validate required headers for each TSV file in a study.'''

        import polars as pl

        errors: List[str] = []
        for label, path in study.files.items():
            expected = required_columns.get(label, ())
            if not expected:
                continue
            frame = pl.read_csv(path, separator='\t', n_rows=1)
            missing = [column for column in expected if column not in frame.columns]
            if missing:
                errors.append(f"{study.study_id}:{label} missing columns {missing}")
        return errors


__all__ = ['REQUIRED_TSVS', 'StudyDiscovery', 'StudyInput']
""",
    "src/etl/transform.py": """'''Transformation logic for metadata and expression data.'''
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Iterator, List

import polars as pl

UNKNOWN_VALUE = 'UNKNOWN'


@dataclass
class MetadataRecord:
    run_id: str
    study_id: str
    subject_id: str
    tissue: str
    disease: str


class MetadataTransformer:
    '''Normalize metadata columns and coalesce missing values.'''

    REQUIRED_COLUMNS = ('study_id', 'subject_id', 'tissue', 'disease')

    def normalize(self, frame: pl.DataFrame, run_id: str) -> List[MetadataRecord]:
        frame = frame.select(self.REQUIRED_COLUMNS).fill_null(UNKNOWN_VALUE)
        return [
            MetadataRecord(
                run_id=run_id,
                study_id=row['study_id'],
                subject_id=row['subject_id'],
                tissue=row['tissue'],
                disease=row['disease'],
            )
            for row in frame.iter_rows(named=True)
        ]


@dataclass
class ExpressionRecord:
    run_id: str
    study_id: str
    ensembl_id: str
    expression: float


class ExpressionFilter:
    '''Stream expression rows and filter based on the configured gene list.'''

    def __init__(self, allowed_genes: Iterable[str]) -> None:
        self._allowed = {gene.upper() for gene in allowed_genes}

    def filter_rows(self, tsv_path: str, study_id: str, run_id: str) -> Iterator[ExpressionRecord]:
        stream = pl.scan_csv(tsv_path, separator='\t', has_header=True)
        for chunk in stream.iter_batches():
            for row in chunk.iter_rows(named=True):
                gene = str(row.get('ensembl_id', '')).upper()
                if gene and (not self._allowed or gene in self._allowed):
                    yield ExpressionRecord(
                        run_id=run_id,
                        study_id=study_id,
                        ensembl_id=gene,
                        expression=float(row.get('expression', 0.0)),
                    )


__all__ = [
    'ExpressionFilter',
    'ExpressionRecord',
    'MetadataRecord',
    'MetadataTransformer',
]
""",
    "src/etl/loader.py": """'''Database loader that batches inserts and upserts using SQLAlchemy.'''
from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass
from typing import Dict, Iterable, Iterator, List, Sequence

from sqlalchemy import insert
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from .checkpoint import CheckpointStore
from ..db import models


@dataclass
class BatchResult:
    table: str
    inserted: int
    skipped: int


class BatchLoader:
    '''Load metadata and expression data with conflict-aware upserts.'''

    def __init__(self, engine: Engine, checkpoint_store: CheckpointStore, batch_size: int = 1000) -> None:
        self._engine = engine
        self._checkpoint_store = checkpoint_store
        self._batch_size = batch_size

    @contextmanager
    def session(self) -> Iterator[Session]:
        session = Session(self._engine)
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def load_metadata(self, records: Sequence) -> BatchResult:
        if not records:
            return BatchResult(table='dim_subject', inserted=0, skipped=0)

        inserted = 0
        skipped = 0
        with self.session() as session:
            for chunk in _chunks(records, self._batch_size):
                payload = [record.__dict__ for record in chunk]
                statement = insert(models.DimSubject).values(payload)
                statement = statement.on_conflict_do_nothing(index_elements=[models.DimSubject.subject_id])
                result = session.execute(statement)
                rowcount = result.rowcount or 0
                inserted += rowcount
                skipped += len(chunk) - rowcount
        return BatchResult(table='dim_subject', inserted=inserted, skipped=skipped)

    def load_expression(self, records: Iterable) -> BatchResult:
        inserted = 0
        skipped = 0
        batch: List[Dict] = []
        with self.session() as session:
            for record in records:
                batch.append(record.__dict__)
                if len(batch) >= self._batch_size:
                    inserted += self._flush_expression(session, batch)
                    batch.clear()
            if batch:
                inserted += self._flush_expression(session, batch)
        return BatchResult(table='fact_expression', inserted=inserted, skipped=skipped)

    def _flush_expression(self, session: Session, batch: List[Dict]) -> int:
        statement = insert(models.FactExpression).values(batch)
        statement = statement.on_conflict_do_nothing(
            index_elements=[
                models.FactExpression.study_id,
                models.FactExpression.ensembl_id,
                models.FactExpression.run_id,
            ]
        )
        result = session.execute(statement)
        return result.rowcount or 0

    def load_checkpoint(self, run_id: str, metadata: Dict[str, str]) -> None:
        self._checkpoint_store.save_checkpoint(run_id, metadata)

    def get_resume_metadata(self, run_id: str) -> Dict[str, str]:
        return self._checkpoint_store.get_checkpoint(run_id)


def _chunks(items: Sequence, chunk_size: int) -> Iterator[Sequence]:
    for index in range(0, len(items), chunk_size):
        yield items[index : index + chunk_size]


__all__ = ['BatchLoader', 'BatchResult', '_chunks']
""",
    "src/etl/checkpoint.py": """'''Checkpoint persistence backed by SQLite.'''
from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Dict


class CheckpointStore:
    '''Maintain checkpoint metadata for resumable ETL runs.'''

    def __init__(self, db_path: Path) -> None:
        self._db_path = db_path
        self._ensure_schema()

    def _ensure_schema(self) -> None:
        with sqlite3.connect(self._db_path) as conn:
            conn.execute(
                '''
                CREATE TABLE IF NOT EXISTS checkpoints (
                    run_id TEXT PRIMARY KEY,
                    metadata TEXT NOT NULL
                )
                '''
            )

    def save_checkpoint(self, run_id: str, metadata: Dict[str, str]) -> None:
        import json

        payload = json.dumps(metadata)
        with sqlite3.connect(self._db_path) as conn:
            conn.execute(
                'REPLACE INTO checkpoints(run_id, metadata) VALUES (?, ?)',
                (run_id, payload),
            )

    def get_checkpoint(self, run_id: str) -> Dict[str, str]:
        import json

        with sqlite3.connect(self._db_path) as conn:
            row = conn.execute(
                'SELECT metadata FROM checkpoints WHERE run_id = ?',
                (run_id,),
            ).fetchone()
        if not row:
            return {}
        return json.loads(row[0])

    def delete_checkpoint(self, run_id: str) -> None:
        with sqlite3.connect(self._db_path) as conn:
            conn.execute('DELETE FROM checkpoints WHERE run_id = ?', (run_id,))


__all__ = ['CheckpointStore']
""",
    "src/etl/rollback.py": """'''Rollback helper that reverses a failed ETL run.'''
from __future__ import annotations

from sqlalchemy import delete
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from ..db import models


class RollbackManager:
    '''Delete rows associated with a specific ``run_id``.'''

    def __init__(self, engine: Engine) -> None:
        self._engine = engine

    def rollback_run(self, run_id: str) -> None:
        with Session(self._engine) as session:
            session.execute(delete(models.FactExpression).where(models.FactExpression.run_id == run_id))
            session.execute(delete(models.DimSubject).where(models.DimSubject.run_id == run_id))
            session.commit()


__all__ = ['RollbackManager']
""",
    "src/db/__init__.py": """'''Database package exports.'''
from .engine import create_engine_from_config
from .mssql import create_mssql_engine
from .sqlite import create_sqlite_engine

__all__ = [
    'create_engine_from_config',
    'create_mssql_engine',
    'create_sqlite_engine',
]
""",
    "src/db/engine.py": """'''Utilities for creating SQLAlchemy engines from configuration.'''
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

from sqlalchemy import create_engine


def create_engine_from_config(config: Dict[str, Any]) -> Any:
    '''Create an engine from the provided configuration dictionary.'''

    backend = config.get('backend', 'sqlite')
    if backend == 'mssql':
        connection_string = config['connection_string']
        return create_engine(connection_string, fast_executemany=True)
    if backend == 'sqlite':
        db_path = Path(config.get('database', 'artifacts.db'))
        return create_engine(f'sqlite:///{db_path}')
    raise ValueError(f'Unsupported backend: {backend}')


__all__ = ['create_engine_from_config']
""",
    "src/db/models.py": """'''SQLAlchemy models for the dimensional schema.'''
from __future__ import annotations

from sqlalchemy import Float, Integer, MetaData, String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

metadata = MetaData()


class Base(DeclarativeBase):
    metadata = metadata


class DimSubject(Base):
    __tablename__ = 'dim_subject'

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    run_id: Mapped[str] = mapped_column(String(36), index=True)
    study_id: Mapped[str] = mapped_column(String(100), index=True)
    subject_id: Mapped[str] = mapped_column(String(100), unique=True)
    tissue: Mapped[str] = mapped_column(String(100))
    disease: Mapped[str] = mapped_column(String(100))


class FactExpression(Base):
    __tablename__ = 'fact_expression'

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    run_id: Mapped[str] = mapped_column(String(36), index=True)
    study_id: Mapped[str] = mapped_column(String(100), index=True)
    ensembl_id: Mapped[str] = mapped_column(String(45), index=True)
    expression: Mapped[float] = mapped_column(Float)


__all__ = ['DimSubject', 'FactExpression', 'Base', 'metadata']
""",
    "src/db/mssql.py": """'''Helpers for creating SQL Server engines.'''
from __future__ import annotations

from typing import Any

from sqlalchemy import create_engine


def create_mssql_engine(server: str, database: str, username: str, password: str, driver: str = 'ODBC Driver 17 for SQL Server') -> Any:
    connection_string = (
        'mssql+pyodbc://'
        f'{username}:{password}@{server}/{database}?driver={driver.replace(" ", "+")}'
    )
    return create_engine(connection_string, fast_executemany=True)


__all__ = ['create_mssql_engine']
""",
    "src/db/sqlite.py": """'''SQLite engine helpers.'''
from __future__ import annotations

from pathlib import Path
from typing import Any

from sqlalchemy import create_engine


def create_sqlite_engine(path: str | Path = 'artifacts.db') -> Any:
    db_path = Path(path)
    return create_engine(f'sqlite:///{db_path}')


__all__ = ['create_sqlite_engine']
""",
    "src/cli/main.py": """'''Typer application exposing ETL commands.'''
from __future__ import annotations

import typer

from . import commands
from ..utils.logging_setup import configure_logging

app = typer.Typer(help='Bioinformatics ETL pipeline CLI')


@app.callback()
def init() -> None:
    configure_logging()


app.command()(commands.run)
app.command()(commands.resume)
app.command()(commands.rollback)
app.command()(commands.validate)
app.command()(commands.report)


if __name__ == '__main__':
    app()
""",
    "src/cli/commands.py": """'''Implementation of ETL CLI commands.'''
from __future__ import annotations

from pathlib import Path
from typing import Optional

import typer

from ..db.engine import create_engine_from_config
from ..etl.checkpoint import CheckpointStore
from ..etl.discovery import StudyDiscovery
from ..etl.loader import BatchLoader
from ..etl.rollback import RollbackManager
from ..etl.transform import ExpressionFilter, MetadataTransformer
from ..utils.file_utils import load_config
from ..utils.metrics import MetricsReporter


def run(config: Path = typer.Option(..., '--config')) -> None:
    settings = load_config(config)
    engine = create_engine_from_config(settings['database'])
    checkpoint = CheckpointStore(Path(settings['artifacts']['database']))
    loader = BatchLoader(engine, checkpoint, batch_size=settings['pipeline']['batch_size'])
    discovery = StudyDiscovery()
    metrics = MetricsReporter()

    run_id = metrics.generate_run_id()
    studies = discovery.discover(Path(settings['input']))

    gene_filter = ExpressionFilter(settings['pipeline']['allowed_genes'])
    transformer = MetadataTransformer()

    for study in studies:
        metadata_records = transformer.normalize(
            metrics.read_metadata(study.files['metadata']),
            run_id=run_id,
        )
        loader.load_metadata(metadata_records)
        expression_rows = gene_filter.filter_rows(
            str(study.files['expression']),
            study_id=study.study_id,
            run_id=run_id,
        )
        loader.load_expression(expression_rows)
        loader.load_checkpoint(run_id, {'study_id': study.study_id})

    typer.echo(f'Run {run_id} completed')


def resume(run_id: str = typer.Argument(...)) -> None:
    typer.echo(f'Resuming run {run_id}')


def rollback(run_id: str = typer.Argument(...), config: Optional[Path] = typer.Option(None, '--config')) -> None:
    settings = load_config(config) if config else {'database': {'backend': 'sqlite'}}
    engine = create_engine_from_config(settings['database'])
    rollback_manager = RollbackManager(engine)
    rollback_manager.rollback_run(run_id)
    typer.echo(f'Rollback for {run_id} complete')


def validate(input_dir: Path = typer.Argument(...)) -> None:
    discovery = StudyDiscovery()
    studies = discovery.discover(input_dir)
    typer.echo(f'Discovered {len(studies)} studies')


def report(run_id: str = typer.Argument(...)) -> None:
    checkpoint = CheckpointStore(Path('artifacts/checkpoints.db'))
    metadata = checkpoint.get_checkpoint(run_id)
    if not metadata:
        typer.echo(f'No checkpoint for {run_id}')
        return
    typer.echo(f'Checkpoint metadata: {metadata}')
""",
    "src/cli/validators.py": """'''Validation helpers for CLI operations.'''
from __future__ import annotations

from pathlib import Path

import typer


def ensure_exists(path: Path) -> Path:
    if not path.exists():
        raise typer.BadParameter(f'Path {path} does not exist')
    return path


__all__ = ['ensure_exists']
""",
    "src/utils/logging_setup.py": """'''Structlog configuration for the ETL CLI.'''
from __future__ import annotations

import logging

import structlog


def configure_logging() -> None:
    logging.basicConfig(level=logging.INFO)
    structlog.configure(
        processors=[
            structlog.processors.TimeStamper(fmt='iso'),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(logging.INFO),
        cache_logger_on_first_use=True,
    )


__all__ = ['configure_logging']
""",
    "src/utils/file_utils.py": """'''Filesystem helpers used across the ETL pipeline.'''
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict

import yaml


def load_config(path: Path) -> Dict[str, Any]:
    if path.suffix in {'.yaml', '.yml'}:
        return yaml.safe_load(path.read_text(encoding='utf-8'))
    if path.suffix == '.json':
        return json.loads(path.read_text(encoding='utf-8'))
    raise ValueError(f'Unsupported config format: {path.suffix}')


__all__ = ['load_config']
""",
    "src/utils/metrics.py": """'''Metrics helper for tracking ETL throughput.'''
from __future__ import annotations

import uuid
from pathlib import Path

import polars as pl


class MetricsReporter:
    def generate_run_id(self) -> str:
        return str(uuid.uuid4())

    def read_metadata(self, path: Path) -> pl.DataFrame:
        return pl.read_csv(path, separator='\t', has_header=True)


__all__ = ['MetricsReporter']
""",
    "migrations/mssql.sql": """CREATE TABLE dim_subject (
    id INT IDENTITY PRIMARY KEY,
    run_id NVARCHAR(36) NOT NULL,
    study_id NVARCHAR(100) NOT NULL,
    subject_id NVARCHAR(100) NOT NULL UNIQUE,
    tissue NVARCHAR(100) NOT NULL,
    disease NVARCHAR(100) NOT NULL
);

CREATE TABLE fact_expression (
    id INT IDENTITY PRIMARY KEY,
    run_id NVARCHAR(36) NOT NULL,
    study_id NVARCHAR(100) NOT NULL,
    ensembl_id NVARCHAR(45) NOT NULL,
    expression FLOAT NOT NULL
);
""",
    "migrations/sqlite.sql": """CREATE TABLE IF NOT EXISTS dim_subject (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id TEXT NOT NULL,
    study_id TEXT NOT NULL,
    subject_id TEXT NOT NULL UNIQUE,
    tissue TEXT NOT NULL,
    disease TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS fact_expression (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id TEXT NOT NULL,
    study_id TEXT NOT NULL,
    ensembl_id TEXT NOT NULL,
    expression REAL NOT NULL
);
""",
    "config/config.example.yaml": """input: ./studies
artifacts:
  database: ./artifacts/checkpoints.db
pipeline:
  batch_size: 1000
  allowed_genes:
    - ENSG000001
    - ENSG000002
    - ENSG000003
database:
  backend: sqlite
  database: ./artifacts/etl.db
""",
    "config/field_mappings.example.yaml": """metadata:
  subject_id: subject_id
  tissue: tissue
  disease: disease
expression:
  gene_column: ensembl_id
  value_column: expression
""",
    "logs/.gitkeep": "",
    "artifacts/.gitkeep": "",
    "dist/.gitkeep": "",
    "tests/test_discovery.py": """'''Tests for study discovery.'''
from __future__ import annotations

from pathlib import Path

from etl.discovery import REQUIRED_TSVS, StudyDiscovery


def test_discovery(tmp_path: Path) -> None:
    study_dir = tmp_path / 'study-a'
    study_dir.mkdir()
    for filename in REQUIRED_TSVS.values():
        (study_dir / filename).write_text('col1\nvalue', encoding='utf-8')

    discovery = StudyDiscovery()
    studies = discovery.discover(tmp_path)
    assert len(studies) == 1
    assert studies[0].study_id == 'study-a'
""",
    "tests/test_transform.py": """'''Tests for metadata transformation and expression filtering.'''
from __future__ import annotations

import polars as pl

from etl.transform import ExpressionFilter, MetadataTransformer


def test_metadata_transformer_normalizes_missing_values() -> None:
    frame = pl.DataFrame(
        {
            'study_id': ['S1'],
            'subject_id': ['SUBJ'],
            'tissue': [None],
            'disease': ['flu'],
        }
    )
    transformer = MetadataTransformer()
    records = transformer.normalize(frame, run_id='run-1')
    assert records[0].tissue == 'UNKNOWN'


def test_expression_filter_streams_records(tmp_path) -> None:
    tsv = tmp_path / 'expression.tsv'
    tsv.write_text('ensembl_id\texpression\nENSG000001\t1.23', encoding='utf-8')
    flt = ExpressionFilter(['ENSG000001'])
    rows = list(flt.filter_rows(str(tsv), study_id='S1', run_id='run-1'))
    assert len(rows) == 1
""",
    "tests/test_loader.py": """'''Tests for the batch loader utility functions.'''
from __future__ import annotations

from etl.loader import _chunks


def test_chunks_splits_sequence() -> None:
    data = list(range(5))
    chunks = list(_chunks(data, 2))
    assert chunks == [data[0:2], data[2:4], data[4:5]]
""",
    "tests/test_resume.py": """'''Tests for checkpoint persistence.'''
from __future__ import annotations

from pathlib import Path

from etl.checkpoint import CheckpointStore


def test_checkpoint_round_trip(tmp_path: Path) -> None:
    store = CheckpointStore(tmp_path / 'ckpt.db')
    store.save_checkpoint('run-1', {'study_id': 'S1'})
    assert store.get_checkpoint('run-1') == {'study_id': 'S1'}
""",
}

__all__ = ["BIOINFORMATICS_ETL_FILES"]
