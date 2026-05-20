# API Notes

## POST /api/v1/verify

Query:

- `user_id`: required string
- `poi_image_path`: optional string

Body:

- `video`: required mp4 file, max 10MB

Response fields:

- `decision`: `approved`, `manual_review`, or `rejected`
- `confidence_score`: overall confidence score
- `similarity_score`: face similarity score
- `liveness_score`: liveness score
- `quality_score`: video quality score
- `reason`: decision reason

## Demo decision testing

Rename your mp4 file to force a result:

- `xxx_pass.mp4` -> approved
- `xxx_review.mp4` -> manual_review
- `xxx_fail.mp4` -> rejected
