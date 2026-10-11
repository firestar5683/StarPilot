#pragma once
#include "rednose/helpers/ekf.h"
extern "C" {
void pose_update_4(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea);
void pose_update_10(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea);
void pose_update_13(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea);
void pose_update_14(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea);
void pose_err_fun(double *nom_x, double *delta_x, double *out_3592422939216669323);
void pose_inv_err_fun(double *nom_x, double *true_x, double *out_6915701396310957140);
void pose_H_mod_fun(double *state, double *out_3743404816978430653);
void pose_f_fun(double *state, double dt, double *out_971936760635752887);
void pose_F_fun(double *state, double dt, double *out_5997582763311156755);
void pose_h_4(double *state, double *unused, double *out_3040948559389363640);
void pose_H_4(double *state, double *unused, double *out_7515212026822338225);
void pose_h_10(double *state, double *unused, double *out_2024725912263715489);
void pose_H_10(double *state, double *unused, double *out_7567938388907257562);
void pose_h_13(double *state, double *unused, double *out_8096238294370646169);
void pose_H_13(double *state, double *unused, double *out_3320900838570512462);
void pose_h_14(double *state, double *unused, double *out_9101361896854545328);
void pose_H_14(double *state, double *unused, double *out_4432423594526965929);
void pose_predict(double *in_x, double *in_P, double *in_Q, double dt);
}