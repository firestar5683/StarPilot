#pragma once
#include "rednose/helpers/ekf.h"
extern "C" {
void pose_update_4(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea);
void pose_update_10(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea);
void pose_update_13(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea);
void pose_update_14(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea);
void pose_err_fun(double *nom_x, double *delta_x, double *out_1366452659282605760);
void pose_inv_err_fun(double *nom_x, double *true_x, double *out_633665134700440095);
void pose_H_mod_fun(double *state, double *out_6557368431862547615);
void pose_f_fun(double *state, double dt, double *out_8766002253507214463);
void pose_F_fun(double *state, double dt, double *out_7027423975176096545);
void pose_h_4(double *state, double *unused, double *out_8406635548758778985);
void pose_H_4(double *state, double *unused, double *out_9087533728568900293);
void pose_h_10(double *state, double *unused, double *out_4724563756245089329);
void pose_H_10(double *state, double *unused, double *out_151772769759508374);
void pose_h_13(double *state, double *unused, double *out_916448766757343904);
void pose_H_13(double *state, double *unused, double *out_1748579136823950394);
void pose_h_14(double *state, double *unused, double *out_4320749477702954633);
void pose_H_14(double *state, double *unused, double *out_6004745296273527997);
void pose_predict(double *in_x, double *in_P, double *in_Q, double dt);
}