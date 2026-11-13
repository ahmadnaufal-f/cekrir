-- CreateSchema
CREATE SCHEMA IF NOT EXISTS "public";

-- CreateEnum
CREATE TYPE "ShipmentStatus" AS ENUM ('pending', 'in_transit', 'delivered', 'exception');

-- CreateEnum
CREATE TYPE "ShipmentSource" AS ENUM ('manual', 'camera');

-- CreateTable
CREATE TABLE "shipment" (
    "id" UUID NOT NULL DEFAULT gen_random_uuid(),
    "resi_number" VARCHAR(64) NOT NULL,
    "courier" VARCHAR(32) NOT NULL,
    "source" "ShipmentSource" NOT NULL,
    "camera_id" VARCHAR(100),
    "status" "ShipmentStatus" NOT NULL DEFAULT 'pending',
    "summary" TEXT NOT NULL,
    "provider" TEXT NOT NULL,
    "history" JSONB NOT NULL DEFAULT '[]',
    "created_at" TIMESTAMPTZ(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "checked_at" TIMESTAMPTZ(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "last_detected_at" TIMESTAMPTZ(3),

    CONSTRAINT "shipment_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "notification" (
    "id" UUID NOT NULL DEFAULT gen_random_uuid(),
    "shipment_id" UUID NOT NULL,
    "title" TEXT NOT NULL,
    "message" TEXT NOT NULL,
    "created_at" TIMESTAMPTZ(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "notification_pkey" PRIMARY KEY ("id")
);

-- CreateIndex
CREATE INDEX "shipment_resi_number_idx" ON "shipment"("resi_number");

-- CreateIndex
CREATE INDEX "shipment_created_at_id_idx" ON "shipment"("created_at" DESC, "id" DESC);

-- CreateIndex
CREATE UNIQUE INDEX "shipment_courier_resi_number_key" ON "shipment"("courier", "resi_number");

-- CreateIndex
CREATE INDEX "notification_shipment_id_idx" ON "notification"("shipment_id");

-- CreateIndex
CREATE INDEX "notification_created_at_id_idx" ON "notification"("created_at" DESC, "id" DESC);

-- AddForeignKey
ALTER TABLE "notification" ADD CONSTRAINT "notification_shipment_id_fkey" FOREIGN KEY ("shipment_id") REFERENCES "shipment"("id") ON DELETE CASCADE ON UPDATE CASCADE;
