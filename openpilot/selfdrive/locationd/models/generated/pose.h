#pragma once
#include "rednose/helpers/ekf.h"
extern "C" {
void pose_update_4(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea);
void pose_update_10(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea);
void pose_update_13(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea);
void pose_update_14(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea);
void pose_err_fun(double *nom_x, double *delta_x, double *out_7162235413577390203);
void pose_inv_err_fun(double *nom_x, double *true_x, double *out_7495913663529407299);
void pose_H_mod_fun(double *state, double *out_170725082104688702);
void pose_f_fun(double *state, double dt, double *out_3543895396835097983);
void pose_F_fun(double *state, double dt, double *out_585703334321150959);
void pose_h_4(double *state, double *unused, double *out_4198313265922725605);
void pose_H_4(double *state, double *unused, double *out_924886084159401309);
void pose_h_10(double *state, double *unused, double *out_331605980695215593);
void pose_H_10(double *state, double *unused, double *out_5486414686034992016);
void pose_h_13(double *state, double *unused, double *out_6500207722279651616);
void pose_H_13(double *state, double *unused, double *out_4137159909491734110);
void pose_h_14(double *state, double *unused, double *out_4036957254120554746);
void pose_H_14(double *state, double *unused, double *out_4888126940498885838);
void pose_predict(double *in_x, double *in_P, double *in_Q, double dt);
}