# Portuguese Parliament Analytics System

A comprehensive analytics processing system for Portuguese Parliamentary data, providing automated calculation of deputy performance metrics, attendance patterns, initiative success rates, and data quality monitoring.

## 🎯 Overview

This system replaces MySQL triggers with reliable Python-based job processing that can be run after data imports or as scheduled jobs. It provides:

- **Real-time Analytics**: Deputy performance scoring (0-100 scale)
- **Attendance Tracking**: Monthly attendance patterns and consistency metrics
- **Initiative Analysis**: Legislative success rates and collaboration tracking
- **Career Progression**: Deputy timeline and milestone tracking
- **Data Quality**: Automated completeness and consistency monitoring

## 📁 System Components

### Core Scripts

1. **`run_analytics.py`** - Simple runner for quick updates
2. **`quick_update_analytics.py`** - Fast updates using stored procedures
3. **`batch_analytics_processor.py`** - Comprehensive batch processing
4. **`calculate_analytics.py`** - Full analytics calculation engine

### Analytics Tables Processed

- `deputy_analytics` - Core performance metrics
- `attendance_analytics` - Monthly attendance patterns
- `initiative_analytics` - Legislative activity tracking
- `deputy_timeline` - Career progression data
- `data_quality_metrics` - Data completeness monitoring

## 🚀 Quick Start

### Prerequisites

1. **Database Setup**: Ensure analytics migration is deployed
```bash
alembic upgrade head  # Deploy analytics tables and stored procedure
```

2. **Test System**: Verify stored procedure is available
```bash
python run_analytics.py --test
```

### Basic Usage

#### Quick Updates (Recommended for regular use)
```bash
# Update recent changes across all legislatures
python run_analytics.py

# Update specific legislature
python run_analytics.py --legislature 15

# Update single deputy
python quick_update_analytics.py --deputy 123
```

#### Full Processing (Use after major data imports)
```bash
# Full recalculation of all analytics
python run_analytics.py --full

# Full processing for specific legislature
python run_analytics.py --full --legislature 15
```

#### Batch Processing (Scheduled jobs)
```bash
# Comprehensive batch processing with reporting
python batch_analytics_processor.py

# Generate report without processing
python batch_analytics_processor.py --report-only
```

## 📊 Analytics Calculated

### Deputy Analytics (0-100 Scoring System)

**Activity Score Composition:**
- **40%** Attendance Score (0-100)
  - Base rate: Session attendance percentage × 0.85
  - Consistency bonus: +15 points for regular attendance patterns
- **30%** Initiative Score (0-100)  
  - Quantity: Logarithmic scale to prevent outlier dominance
  - Success rate: Approval percentage × 0.35
  - Collaboration: Multi-author initiatives × 0.15
- **20%** Intervention Score (0-100)
  - Frequency: Parliamentary speech count (logarithmic)
  - Substance: Average word count per intervention
- **10%** Engagement Score (placeholder for future enhancement)

### Attendance Analytics

**Monthly Tracking:**
- Sessions scheduled/attended/absent
- Attendance rate percentage
- Consistency patterns
- Punctuality metrics (future)

### Initiative Analytics

**Legislative Activity:**
- Total initiatives authored/co-authored
- Success rates by initiative type
- Cross-party collaboration metrics
- Temporal productivity patterns

### Deputy Timeline

**Career Progression:**
- Total legislatures served
- Years of service calculation
- Experience categorization (junior/mid-career/senior/veteran)
- Key milestone tracking

### Data Quality Metrics

**Automated Monitoring:**
- Record completeness percentages
- Consistency scores
- Referential integrity validation
- Temporal data logic checks

## 🔧 Integration Guide

### Post-Import Processing

Add to your data import scripts:

```python
# After successful data import
from scripts.analytics.run_analytics import run_quick_analytics

# Update analytics for the imported legislature
success = run_quick_analytics(legislatura_id=15)
if success:
    print("Analytics updated successfully")
```

### Scheduled Jobs

#### Daily Quick Updates (Recommended)
```bash
# Add to crontab for daily updates at 2 AM
0 2 * * * cd /path/to/parliament && python scripts/analytics/run_analytics.py
```

#### Weekly Full Processing
```bash
# Weekly comprehensive recalculation on Sundays at 3 AM
0 3 * * 0 cd /path/to/parliament && python scripts/analytics/run_analytics.py --full
```

### Workflow Integration

```python
# Example integration in data processing workflow
def import_parliament_data(xml_file, legislatura_id):
    try:
        # 1. Import data
        import_results = process_xml_data(xml_file, legislatura_id)
        
        # 2. Update analytics
        from scripts.analytics.quick_update_analytics import QuickAnalyticsUpdater
        updater = QuickAnalyticsUpdater(get_db_connection())
        
        # Update recent changes for this legislature
        updated_count = updater.update_recent_changes(legislatura_id, hours=1)
        
        print(f"Import completed: {import_results['records']} records, {updated_count} analytics updated")
        
    except Exception as e:
        print(f"Import failed: {e}")
```

## 📈 Performance Characteristics

### Quick Updates (Stored Procedure)
- **Speed**: ~50-100 deputies/second
- **Memory**: Low (single deputy processing)
- **Use case**: Regular updates, post-import processing

### Batch Processing (Python Calculation)
- **Speed**: ~10-20 deputies/second (more comprehensive)
- **Memory**: Moderate (batch operations)
- **Use case**: Full recalculation, scheduled jobs

### Scaling Guidelines
- **< 1,000 deputies**: Any method works well
- **1,000-10,000 deputies**: Use quick updates for regular processing
- **> 10,000 deputies**: Consider chunked batch processing

## 🛠️ Advanced Usage

### Custom Legislature Processing
```python
from scripts.analytics.calculate_analytics import AnalyticsCalculator

engine = get_db_connection()
calculator = AnalyticsCalculator(engine, verbose=True)

# Process specific legislature with force refresh
calculator.calculate_all_analytics(legislatura_id=15, force_refresh=True)
```

### Error Handling and Monitoring
```python
from scripts.analytics.batch_analytics_processor import BatchAnalyticsProcessor

processor = BatchAnalyticsProcessor(engine, verbose=True)
processor.process_all_analytics()

# Check processing statistics
if processor.stats.errors:
    print(f"Errors encountered: {len(processor.stats.errors)}")
    # Handle errors appropriately
```

### Custom Scoring Adjustments

The scoring algorithms can be adjusted by modifying the calculation methods in `calculate_analytics.py`:

```python
# Example: Adjust activity score weights
def _calculate_activity_score(self, attendance_data, initiative_data, intervention_data):
    composite_score = (
        (attendance_data['score'] * 0.50) +    # Increase attendance weight
        (initiative_data['score'] * 0.25) +     # Decrease initiative weight
        (intervention_data['score'] * 0.25) +   # Increase intervention weight
        (0 * 0.00)  # Remove engagement for now
    )
    return min(100, max(0, int(round(composite_score))))
```

## 🐛 Troubleshooting

### Common Issues

1. **Stored Procedure Not Found**
```bash
# Run the analytics migration
alembic upgrade head

# Test availability
python run_analytics.py --test
```

2. **MySQL Privilege Errors**
```bash
# The system is designed to work without SUPER privileges
# Use Python processing instead of triggers
python run_analytics.py --full
```

3. **Performance Issues**
```bash
# Use quick updates for regular processing
python run_analytics.py

# Limit to specific legislature for large datasets
python run_analytics.py --legislature 15
```

4. **Memory Issues with Large Datasets**
```bash
# Process legislatures individually
for leg in {1..15}; do
    python run_analytics.py --legislature $leg
done
```

### Logging and Monitoring

Processing logs are automatically saved to `scripts/analytics/logs/`:
- Batch processing creates detailed JSON logs
- Quick updates log to console
- Error details included for debugging

### Performance Optimization

1. **Database Indexes**: Ensure Phase 1 performance indexes are deployed
2. **Batch Size**: Adjust session commit frequency for large datasets
3. **Parallel Processing**: Run different legislatures in parallel
4. **Resource Monitoring**: Monitor CPU/memory usage during large runs

## 📋 API Reference

### QuickAnalyticsUpdater Methods

- `update_deputy_analytics(deputado_id, legislatura_id)` - Update single deputy
- `update_recent_changes(legislatura_id, hours)` - Update recent activity
- `bulk_update_legislature(legislatura_id)` - Update entire legislature
- `test_stored_procedure()` - Test system availability

### BatchAnalyticsProcessor Methods

- `process_all_analytics(legislatura_id, report_only)` - Main processing method
- Processing components for each analytics table type
- Comprehensive error handling and reporting

### AnalyticsCalculator Methods

- `calculate_all_analytics(legislatura_id, force_refresh)` - Full calculation
- Individual metric calculation methods
- Flexible parameter handling

## 🤝 Contributing

When extending the analytics system:

1. **Add new metrics** by extending the calculation classes
2. **Modify scoring** by adjusting the weight parameters
3. **Add new analytics tables** by creating corresponding processing methods
4. **Maintain backward compatibility** with existing analytics data

## 📄 License

This analytics system is part of the Portuguese Parliament data processing project.