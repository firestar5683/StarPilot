#pragma once
#include "rednose/helpers/ekf.h"
extern "C" {
void pose_update_4(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea);
void pose_update_10(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea);
void pose_update_13(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea);
void pose_update_14(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea);
void pose_err_fun(double *nom_x, double *delta_x, double *out_8587424029422482613);
void pose_inv_err_fun(double *nom_x, double *true_x, double *out_8786163150320395038);
void pose_H_mod_fun(double *state, double *out_2404492370394702667);
void pose_f_fun(double *state, double dt, double *out_442464745730678105);
void pose_F_fun(double *state, double dt, double *out_68862599699564370);
void pose_h_4(double *state, double *unused, double *out_6968799398651119641);
void pose_H_4(double *state, double *unused, double *out_6333703861688286471);
void pose_h_10(double *state, double *unused, double *out_5068008641526453532);
void pose_H_10(double *state, double *unused, double *out_3796470789070264043);
void pose_h_13(double *state, double *unused, double *out_1215417763549020361);
void pose_H_13(double *state, double *unused, double *out_8900766386688932344);
void pose_h_14(double *state, double *unused, double *out_1254666721235298923);
void pose_H_14(double *state, double *unused, double *out_8149799355681780616);
void pose_predict(double *in_x, double *in_P, double *in_Q, double dt);
}